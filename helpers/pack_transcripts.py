#!/usr/bin/env python3
"""
pack_transcripts.py — Caveman-Video Transcript Shrinker
Converts verbose Whisper / ElevenLabs Scribe JSON transcripts into:
  1. edit/takes_packed.md  (Phrase-level view broken on silence >= 0.5s; ~90% fewer tokens)
  2. edit/words_timed.txt  (Compact start\tend\tword table for word-boundary cuts)
  3. edit/captions.tsv     (Grouped 4-6 word editorial caption chunks for native/overlay renderers)
"""

import argparse
import glob
import json
import os
from pathlib import Path


def extract_words(data):
    """Support both ElevenLabs Scribe ({words: [...]}) and HyperFrames/Whisper flat or segment formats."""
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        if "words" in data and isinstance(data["words"], list):
            raw = data["words"]
        elif "segments" in data and isinstance(data["segments"], list):
            raw = []
            for seg in data["segments"]:
                if "words" in seg:
                    raw.extend(seg["words"])
                else:
                    raw.append(seg)
        else:
            raw = []
    else:
        raw = []

    words = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        wtype = item.get("type", "word")
        if wtype == "spacing":
            continue
        text = (item.get("text") or item.get("word") or "").strip()
        if not text:
            continue
        start = float(item.get("start", item.get("start_time", 0.0)))
        end = float(item.get("end", item.get("end_time", start)))
        speaker = item.get("speaker_id") or item.get("speaker") or "S0"
        words.append({"text": text, "start": start, "end": end, "speaker": str(speaker)})
    return words


def build_phrases(words, silence_gap=0.5):
    phrases = []
    if not words:
        return phrases
    cur = {
        "start": words[0]["start"],
        "end": words[0]["end"],
        "speaker": words[0]["speaker"],
        "words": [words[0]],
    }
    for w in words[1:]:
        gap = w["start"] - cur["end"]
        if gap >= silence_gap or w["speaker"] != cur["speaker"]:
            phrases.append(cur)
            cur = {"start": w["start"], "end": w["end"], "speaker": w["speaker"], "words": [w]}
        else:
            cur["end"] = w["end"]
            cur["words"].append(w)
    phrases.append(cur)
    return phrases


def build_caption_chunks(words, max_words=5, max_gap=0.45):
    chunks = []
    if not words:
        return chunks
    cur = [words[0]]
    for w in words[1:]:
        gap = w["start"] - cur[-1]["end"]
        prev_punct = cur[-1]["text"].endswith((".", "!", "?", ",", ";", ":"))
        if len(cur) >= max_words or gap >= max_gap or (prev_punct and len(cur) >= 3):
            chunks.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Pack verbose ASR JSON into compact Caveman-Video formats.")
    parser.add_argument("--edit-dir", default="edit", help="Path to edit directory containing transcripts/")
    parser.add_argument("--silence-gap", type=float, default=0.5, help="Silence threshold in seconds to split phrases")
    args = parser.parse_args()

    edit_dir = Path(args.edit_dir)
    tx_dir = edit_dir / "transcripts"
    json_files = sorted(glob.glob(str(tx_dir / "*.json")))
    if not json_files:
        print(f"No transcript JSON files found in {tx_dir}")
        return

    packed_lines = ["# Packed Transcripts (`takes_packed.md`)\n"]
    all_words_lines = []
    caption_tsv_lines = []

    for jf in json_files:
        stem = Path(jf).stem
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)

        words = extract_words(data)
        if not words:
            continue

        phrases = build_phrases(words, silence_gap=args.silence_gap)
        dur = words[-1]["end"]
        packed_lines.append(f"## {stem} (duration: {dur:.2f}s, {len(phrases)} phrases, {len(words)} words)")
        for p in phrases:
            txt = " ".join(w["text"] for w in p["words"])
            packed_lines.append(f"  [{p['start']:06.2f}-{p['end']:06.2f}] {p['speaker']} {txt}")
        packed_lines.append("")

        for w in words:
            all_words_lines.append(f"{w['start']:.2f}\t{w['end']:.2f}\t{w['text']}")

        chunks = build_caption_chunks(words)
        for ch in chunks:
            c_start = ch[0]["start"]
            c_end = ch[-1]["end"]
            tokens_str = " ".join(f"{w['start']:.2f}|{w['end']:.2f}|{w['text']}" for w in ch)
            caption_tsv_lines.append(f"{c_start:.2f}\t{c_end:.2f}\t{tokens_str}")

    takes_path = edit_dir / "takes_packed.md"
    words_path = edit_dir / "words_timed.txt"
    caps_path = edit_dir / "captions.tsv"

    takes_path.write_text("\n".join(packed_lines), encoding="utf-8")
    words_path.write_text("\n".join(all_words_lines) + "\n", encoding="utf-8")
    caps_path.write_text("\n".join(caption_tsv_lines) + "\n", encoding="utf-8")

    print(
        f"packed {len(json_files)} transcript(s) -> "
        f"{takes_path} ({len(packed_lines)} lines), "
        f"{words_path} ({len(all_words_lines)} words), "
        f"{caps_path} ({len(caption_tsv_lines)} caption groups)"
    )


if __name__ == "__main__":
    main()
