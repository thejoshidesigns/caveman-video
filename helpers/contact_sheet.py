#!/usr/bin/env python3
"""
contact_sheet.py — Caveman-Video Vision Token Shrinker
Tiles N preview PNG frames (or samples N frames directly from an MP4) into ONE
labeled grid PNG so the agent inspects 12-16 keyframes in a single image call
(-90% vision token cost).
"""

import argparse
import math
import subprocess
import sys
from pathlib import Path


def sample_video_contact_sheet(video_path: str, out_path: str, count: int = 12, cols: int = 4):
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ],
        capture_output=True, text=True, check=True
    )
    duration = max(1.0, float(probe.stdout.strip()))
    rows = math.ceil(count / cols)
    fps_val = count / duration

    vf = (
        f"fps={fps_val:.5f},"
        f"scale=480:-1,"
        f"drawtext=text='%{{pts\\:hms}}':x=12:y=12:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.65,"
        f"tile={cols}x{rows}:padding=6:margin=6:color=0x141418"
    )
    cmd = ["ffmpeg", "-y", "-v", "warning", "-i", video_path, "-vf", vf, "-frames:v", "1", out_path]
    subprocess.run(cmd, check=True)
    print(f"contact_sheet: {out_path} ({cols}x{rows} grid from {video_path}, {duration:.2f}s)")


def tile_pngs_contact_sheet(png_paths, out_path: str, cols: int = 4):
    n = len(png_paths)
    rows = math.ceil(n / cols)
    inputs = []
    filter_parts = []
    for i, p in enumerate(png_paths):
        inputs.extend(["-i", str(p)])
        label = Path(p).stem.replace(":", "\\:")
        filter_parts.append(
            f"[{i}:v]scale=480:-1,"
            f"drawtext=text='{label}':x=12:y=12:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.65[v{i}]"
        )
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(
        f"{concat_in}concat=n={n}:v=1:a=0,tile={cols}x{rows}:padding=6:margin=6:color=0x141418[out]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "warning",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[out]", "-frames:v", "1", out_path
    ]
    subprocess.run(cmd, check=True)
    print(f"contact_sheet: {out_path} ({n} frames tiled in {cols}x{rows})")


def main():
    parser = argparse.ArgumentParser(description="Tile preview frames or video timestamps into one contact sheet PNG.")
    parser.add_argument("inputs", nargs="+", help="Input PNG files or a single MP4/MOV video file")
    parser.add_argument("-o", "--output", default="edit/preview_frames/contact_sheet.png", help="Output PNG path")
    parser.add_argument("--cols", type=int, default=4, help="Columns in tile grid")
    parser.add_argument("--count", type=int, default=12, help="Number of frames when sampling from a video")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    first = Path(args.inputs[0])
    if len(args.inputs) == 1 and first.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
        sample_video_contact_sheet(str(first), args.output, count=args.count, cols=args.cols)
    else:
        tile_pngs_contact_sheet(args.inputs, args.output, cols=args.cols)


if __name__ == "__main__":
    main()
