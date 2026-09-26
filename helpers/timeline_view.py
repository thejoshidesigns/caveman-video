#!/usr/bin/env python3
"""
timeline_view.py — Caveman-Video Cut-Boundary Filmstrip + Audio Waveform Inspector
Generates a composite PNG showing the 6-frame filmstrip on top and the audio
waveform on the bottom for a [start, end] window. Used by cavecrew-qc to verify
cut boundaries, audio pops, and subtitle occlusion.
"""

import argparse
import subprocess
from pathlib import Path


def render_timeline_view(video_path: str, start: float, end: float, out_path: str, frames: int = 6):
    dur = max(0.2, end - start)
    fps_val = frames / dur
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    fc = (
        f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps_val:.4f},scale=320:180,"
        f"drawtext=text='%{{pts\\:flt}}s':x=8:y=8:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
        f"tile={frames}x1:padding=4:margin=4:color=0x111115[strip];"
        f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS,"
        f"showwavespic=s={320*frames + 4*(frames+1)}x140:colors=0xA084E8|0x2CD3C0:split_channels=0,"
        f"drawbox=x=iw/2-1:y=0:w=2:h=ih:color=0xFF5A00@0.85:t=fill[wave];"
        f"[strip][wave]vstack=inputs=2[out]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "warning",
        "-i", video_path,
        "-filter_complex", fc,
        "-map", "[out]", "-frames:v", "1", out_path
    ]
    subprocess.run(cmd, check=True)
    print(f"timeline_view: {out_path} ([{start:.2f}s - {end:.2f}s], {frames} frames + waveform)")


def main():
    parser = argparse.ArgumentParser(description="Render filmstrip + waveform PNG for a time window.")
    parser.add_argument("video", help="Input video file")
    parser.add_argument("start", type=float, help="Start time in seconds")
    parser.add_argument("end", type=float, help="End time in seconds")
    parser.add_argument("-o", "--output", default="edit/verify_frames/timeline_view.png", help="Output PNG path")
    args = parser.parse_args()
    render_timeline_view(args.video, args.start, args.end, args.output)


if __name__ == "__main__":
    main()
