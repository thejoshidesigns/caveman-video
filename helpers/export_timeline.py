#!/usr/bin/env python3
"""
export_timeline.py — Non-Destructive NLE Timeline Exporter (.fcpxml & .otio)
Converts edit/edl.json or edit/storyboard.json into:
  1. Final Cut Pro XML v1.10 (.fcpxml) — compatible with DaVinci Resolve, Final Cut Pro, Premiere Pro
  2. OpenTimelineIO (.otio) — universal JSON timeline schema
"""

import argparse
import json
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET


def sec_to_rational(sec: float, fps: int = 25) -> str:
    """Snap seconds to exact frame boundary rational string for FCPXML (e.g. '2500/2500s')."""
    frames = round(sec * fps)
    num = frames * 100
    den = fps * 100
    return f"{num}/{den}s"


def export_fcpxml(edl: dict, out_path: Path, width: int = 1920, height: int = 1080, fps: int = 25):
    fcpxml = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(fcpxml, "resources")

    frame_dur = f"100/{fps * 100}s"
    ET.SubElement(
        resources, "format",
        id="r1",
        name=f"FFVideoFormat{height}p{fps}",
        frameDuration=frame_dur,
        width=str(width),
        height=str(height),
        colorSpace="1-1-1 (Rec. 709)"
    )

    sources = edl.get("sources", {})
    asset_ids = {}
    idx = 2
    for key, src_path in sources.items():
        aid = f"r{idx}"
        idx += 1
        asset_ids[key] = aid
        uri = Path(src_path).resolve().as_uri()
        asset = ET.SubElement(
            resources, "asset",
            id=aid, name=key, start="0s", duration="360000/100s",
            hasVideo="1", hasAudio="1", format="r1"
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=uri)

    overlays = edl.get("overlays", [])
    overlay_ids = []
    for ov in overlays:
        aid = f"r{idx}"
        idx += 1
        overlay_ids.append((aid, ov))
        uri = Path(ov["file"]).resolve().as_uri()
        asset = ET.SubElement(
            resources, "asset",
            id=aid, name=Path(ov["file"]).stem, start="0s",
            duration=sec_to_rational(float(ov.get("duration", 5.0)), fps),
            hasVideo="1", hasAudio="0", format="r1"
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=uri)

    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", name="Caveman-Video Edit")
    project = ET.SubElement(event, "project", name=edl.get("title", "Caveman-Video Timeline"))

    ranges = edl.get("ranges", [])
    total_sec = sum(float(r["end"]) - float(r["start"]) for r in ranges)
    sequence = ET.SubElement(
        project, "sequence",
        format="r1",
        duration=sec_to_rational(total_sec, fps),
        tcStart="0s", tcFormat="NDF",
        audioLayout="stereo", audioRate="48k"
    )
    spine = ET.SubElement(sequence, "spine")

    cur_offset = 0.0
    for i, r in enumerate(ranges):
        src_key = r["source"]
        aid = asset_ids.get(src_key, "r2")
        start_s = float(r["start"])
        dur_s = max(0.04, float(r["end"]) - start_s)
        beat = r.get("beat", f"Cut_{i+1}")
        clip = ET.SubElement(
            spine, "asset-clip",
            name=f"{src_key} - {beat}",
            ref=aid,
            offset=sec_to_rational(cur_offset, fps),
            start=sec_to_rational(start_s, fps),
            duration=sec_to_rational(dur_s, fps),
            format="r1",
            tcFormat="NDF"
        )
        if r.get("reason") or r.get("quote"):
            ET.SubElement(
                clip, "marker",
                start=sec_to_rational(start_s, fps),
                duration=frame_dur,
                value=f"{beat}: {r.get('reason', r.get('quote', ''))}"
            )
        if i == 0 and overlay_ids:
            for ov_aid, ov in overlay_ids:
                ov_start = float(ov.get("start_in_output", 0.0))
                ov_dur = float(ov.get("duration", 5.0))
                ET.SubElement(
                    clip, "asset-clip",
                    name=Path(ov["file"]).stem,
                    lane="1",
                    ref=ov_aid,
                    offset=sec_to_rational(start_s + ov_start, fps),
                    start="0s",
                    duration=sec_to_rational(ov_dur, fps),
                    format="r1"
                )
        cur_offset += dur_s

    tree = ET.ElementTree(fcpxml)
    ET.indent(tree, space="  ")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)
    print(f"exported FCPXML v1.10 -> {out_path} ({len(ranges)} cuts, {len(overlay_ids)} overlays, {total_sec:.2f}s)")


def export_otio(edl: dict, out_path: Path, fps: int = 25):
    sources = edl.get("sources", {})
    ranges = edl.get("ranges", [])
    v1_children = []
    for r in ranges:
        src_key = r["source"]
        start_f = round(float(r["start"]) * fps)
        dur_f = max(1, round((float(r["end"]) - float(r["start"])) * fps))
        v1_children.append({
            "OTIO_SCHEMA": "Clip.2",
            "name": f"{src_key}_{r.get('beat', 'CUT')}",
            "metadata": {"beat": r.get("beat", ""), "reason": r.get("reason", ""), "quote": r.get("quote", "")},
            "source_range": {
                "OTIO_SCHEMA": "TimeRange.1",
                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": start_f, "rate": fps},
                "duration": {"OTIO_SCHEMA": "RationalTime.1", "value": dur_f, "rate": fps}
            },
            "media_reference": {
                "OTIO_SCHEMA": "ExternalReference.1",
                "target_url": str(Path(sources.get(src_key, src_key)).resolve())
            }
        })

    otio_doc = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": edl.get("title", "Caveman-Video Timeline"),
        "global_start_time": {"OTIO_SCHEMA": "RationalTime.1", "value": 0, "rate": fps},
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "name": "tracks",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "V1_Primary",
                    "kind": "Video",
                    "children": v1_children
                }
            ]
        }
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(otio_doc, indent=2), encoding="utf-8")
    print(f"exported OpenTimelineIO -> {out_path} ({len(v1_children)} clips @ {fps}fps)")


def main():
    parser = argparse.ArgumentParser(description="Export edl.json to .fcpxml and .otio NLE timelines.")
    parser.add_argument("--input", default="edit/edl.json", help="Input EDL JSON path")
    parser.add_argument("--fcpxml", default="edit/timeline.fcpxml", help="Output .fcpxml path")
    parser.add_argument("--otio", default="edit/timeline.otio", help="Output .otio path")
    parser.add_argument("--fps", type=int, default=25, help="Sequence frame rate")
    parser.add_argument("--width", type=int, default=1920, help="Sequence width")
    parser.add_argument("--height", type=int, default=1080, help="Sequence height")
    args = parser.parse_args()

    edl = json.loads(Path(args.input).read_text(encoding="utf-8"))
    export_fcpxml(edl, Path(args.fcpxml), width=args.width, height=args.height, fps=args.fps)
    export_otio(edl, Path(args.otio), fps=args.fps)


if __name__ == "__main__":
    main()
