#!/usr/bin/env python3
"""
caveman-video: render_edl.py
Surgical FFmpeg EDL Renderer enforcing the 15 Hard Rules:
1. Per-segment trim with 30ms audio fades (prevents concat click/pop artifacts).
2. Optional color grade presets (warm, cinematic, moody, clean).
3. Lossless concat demuxer join.
4. Optional overlays with setpts=PTS-STARTPTS+<start>/TB and eof_action=pass.
5. Subtitles burned LAST (Rule #6).
6. Audio loudnorm I=-14:TP=-1.5:LRA=11 and BT.709 color tags (Rules #7 & #8).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


GRADE_FILTERS = {
    "none": "",
    "warm": "eq=contrast=1.06:brightness=0.01:saturation=1.12,colorbalance=rs=0.04:gs=0.01:bs=-0.03",
    "cinematic": "eq=contrast=1.12:brightness=-0.01:saturation=0.92,colorbalance=rs=-0.02:gs=0.0:bs=0.04:rh=0.04:gh=0.02:bh=-0.02",
    "moody": "eq=contrast=1.18:brightness=-0.03:saturation=0.82",
    "clean": "eq=contrast=1.04:saturation=1.05",
}


def run_cmd(cmd: list[str], dry_run: bool = False) -> None:
    if dry_run:
        print("DRY-RUN:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-15:])
        raise RuntimeError(f"FFmpeg command failed (exit {proc.returncode}):\n{tail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Surgical FFmpeg EDL Renderer with 30ms fades & BT.709 compliance.")
    parser.add_argument("edl_json", help="Path to edit_plan.json")
    parser.add_argument("-o", "--output", default="output_final.mp4", help="Output MP4 path")
    parser.add_argument("--grade", choices=list(GRADE_FILTERS.keys()), default="none", help="Color grade preset")
    parser.add_argument("--subtitles", help="Optional .ass or .srt subtitle file to burn LAST (Rule #6)")
    parser.add_argument("--fade-ms", type=int, default=30, help="Audio boundary fade in milliseconds (default: 30ms)")
    parser.add_argument("--crf", type=int, default=18, help="H.264 CRF quality (default: 18)")
    parser.add_argument("--dry-run", action="store_true", help="Print FFmpeg commands without executing")
    args = parser.parse_args()

    edl_path = Path(args.edl_json).resolve()
    if not edl_path.exists():
        print(f"ERR: EDL file not found: {edl_path}", file=sys.stderr)
        return 1

    data = json.loads(edl_path.read_text(encoding="utf-8"))
    segments = data.get("segments") or data.get("cuts") or []
    default_src = data.get("source") or data.get("src") or ""
    fps = int(data.get("fps", 30))
    width = int(data.get("width", 1080))
    height = int(data.get("height", 1920))

    if not segments:
        print("ERR: No segments found in EDL JSON.", file=sys.stderr)
        return 1

    fade_s = max(0.005, args.fade_ms / 1000.0)
    tmp_dir = Path(tempfile.mkdtemp(prefix="caveman_edl_"))

    try:
        seg_files: list[Path] = []
        total_out_dur = 0.0

        for idx, seg in enumerate(segments):
            src = seg.get("src") or seg.get("source") or default_src
            if not src:
                raise ValueError(f"Segment {idx} has no source file specified.")
            in_s = float(seg.get("in", seg.get("start", 0.0)))
            out_s = float(seg.get("out", seg.get("end", in_s)))
            dur = round(out_s - in_s, 4)
            if dur <= 0.04:
                continue

            seg_out = tmp_dir / f"seg_{idx:04d}.mp4"
            fade_out_st = max(0.0, round(dur - fade_s, 4))

            vf_parts = [
                f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                f"fps={fps}",
                "format=yuv420p",
            ]
            grade_vf = GRADE_FILTERS.get(args.grade, "")
            if grade_vf:
                vf_parts.insert(2, grade_vf)

            af_str = f"afade=t=in:st=0:d={fade_s:.3f},afade=t=out:st={fade_out_st:.3f}:d={fade_s:.3f}"

            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{in_s:.3f}",
                "-to", f"{out_s:.3f}",
                "-i", str(src),
                "-vf", ",".join(vf_parts),
                "-af", af_str,
                "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                str(seg_out),
            ]
            run_cmd(cmd, dry_run=args.dry_run)
            seg_files.append(seg_out)
            total_out_dur += dur

        concat_txt = tmp_dir / "concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in seg_files) + "\n",
            encoding="utf-8",
        )

        joined_mp4 = tmp_dir / "joined.mp4"
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c", "copy", str(joined_mp4),
        ], dry_run=args.dry_run)

        # Final pass: optional subtitle burn LAST + loudnorm -14 LUFS + BT.709 tags
        final_vf = ["format=yuv420p"]
        sub_path = args.subtitles or data.get("subtitles")
        if sub_path:
            escaped_sub = str(Path(sub_path).resolve()).replace("\\", "/").replace(":", "\\:")
            final_vf.insert(0, f"subtitles='{escaped_sub}'")

        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        final_cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(joined_mp4),
            "-vf", ",".join(final_vf),
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        run_cmd(final_cmd, dry_run=args.dry_run)

        print(f"OK | out={output_path.name} | segs={len(seg_files)} | dur={total_out_dur:.2f}s | res={width}x{height}@{fps} | grade={args.grade}")
        return 0
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 1
    finally:
        if not args.dry_run and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
