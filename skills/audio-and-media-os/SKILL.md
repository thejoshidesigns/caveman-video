---
name: audio-and-media-os
description: >
  Media asset resolution (BGM, SFX, images, icons, official brand logos, TTS
  voiceover, LUTs), audio defect diagnosis, dynamic voiceover frequency carving
  (400Hz / 1kHz / 1.6kHz), 30ms cut boundary fades, and EBU R128 loudness
  mastering. Consolidates media-use and hyperframes-audio.
---

# Audio Mixing & Agent Media OS (`audio-and-media-os`)

A mix is a set of frequency and dynamic relationships, not a stack of random filters. Subtract rumble/mud before compressing, carve the music bed around the human voice, fade every cut boundary by 30ms, and normalize master loudness.

---

## 1. One-Verb Media Resolution (`media-use`)

When inside a HyperFrames project (or resolving catalog assets), use one command so search noise stays on disk:
```bash
npx hyperframes media-use resolve --type <bgm|sfx|image|icon|logo|voice|grade|lut> --intent "<description>" --project <dir>
```
- **Official Brand Logos (`--type logo`):** Resolves official SVG/vector marks (`svgl → simple-icons → GitHub avatar → favicon`). **Never redraw or hallucinate a company logo SVG by hand.**
- **Proactive Media Opportunity Scan (Ask Once):**
  Scan the composition once and propose a consolidated upgrade list (user approves **all / some / none**):
  - Silent transitions/cuts → offer subtle transition `sfx`
  - Piece $>10\text{s}$ with no music bed → offer `bgm`
  - Emoji or fake `<div>` icon → resolve real transparent `icon`
  - Under/over-exposed footage → propose corrective `grade`

---

## 2. Audio Diagnosis & Symptom-to-Fix Table (`hyperframes-audio`)

> **Golden Rule of Audio Diagnosis:** Never judge a single unknown voice against a generic reference spectrum. Compare speech segments against **silence/room-tone gaps inside the same file** to isolate channel noise/resonances from speaker formants.

### Signal Processing Order
Always chain processors in this exact order:
1. **Subtract (Filters):** High-pass rumble (`80Hz`) and cut mud (`200–250Hz`) *before* dynamics so the compressor doesn't chase low-end thumps.
2. **Level (Dynamics):** Gate room tone (`room-gate`) → Compress voice (`compressor` 3:1, attack `15ms`, release `120ms`).
3. **Relationships (Voiceover Carve / Sidechain Ducking):** Carve the music bed so speech owns `1–3kHz`.
4. **Ceiling (Master Limiter / Loudnorm):** EBU R128 `-14 LUFS`, true peak `-1.0 dBTP`.

| Audible Symptom | Frequency / Cause | Surgical Fix (FFmpeg / Web Audio Preset) |
| :--- | :--- | :--- |
| Low hum / mic stand thump | $< 80\text{Hz}$ rumble | `highpass=f=80` (`rumble-cut`) |
| Boomy / chesty voice | $180–220\text{Hz}$ buildup | `equalizer=f=200:t=q:w=1.5:g=-3.5` (*Tame Boominess*) |
| Muffled / "behind cardboard" | $250–300\text{Hz}$ mud | `equalizer=f=250:t=q:w=1.4:g=-3.0` (*Reduce Mud*) |
| Words hard to distinguish | Masking at $2.5–3.5\text{kHz}$ | `equalizer=f=3000:t=q:w=1.2:g=2.5` (*Add Clarity*) + **Carve BGM** |
| Harsh / piercing sibilance | $3.2–6\text{kHz}$ spike | `equalizer=f=3200:t=q:w=1.8:g=-2.5` (*Soften Harshness*) |
| Audible click/pop at video cut | Missing boundary envelope | **Hard Rule 3:** `afade=t=in:st=0:d=0.03,afade=t=out:st={dur-0.03}:d=0.03` |

---

## 3. Voiceover Frequency Carve & Ducking (Speech vs. Music Bed)

Turning a music bed all the way down makes a video feel empty; leaving it loud masks speech. **Carve the vocal formants (`400Hz`, `1kHz`, `1.6kHz–3kHz`) out of the music bed** while ducking overall bed gain during active speech:

### A. In FFmpeg (Surgical EQ Carve + Sidechain Compression)
```bash
# Carve vocal presence bands from BGM [1:a] and sidechain-duck under Voice [0:a]
ffmpeg -y -i voice.wav -i bgm.mp3 -filter_complex \
  "[0:a]highpass=f=80,equalizer=f=250:t=q:w=1.4:g=-2.5,acompressor=threshold=-18dB:ratio=3:attack=15:release=120:makeup=2[vox]; \
   [1:a]volume=0.35,equalizer=f=400:t=q:w=1.2:g=-3.0,equalizer=f=1000:t=q:w=1.0:g=-4.5,equalizer=f=2400:t=q:w=1.0:g=-5.0[bed_eq]; \
   [bed_eq][vox]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=350[bed_duck]; \
   [vox][bed_duck]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:TP=-1.0:LRA=11[aout]" \
  -map "[aout]" -c:a aac -b:a 192k mixed_master.m4a
```

### B. In HyperFrames (`data-fx-carve` & `<hf-audio-group>`)
Use `scripts/carve.mjs` or `data-fx-carve` on the music bed element to automatically generate dynamic peaking dips (`400Hz`, `1kHz`, `1.6kHz`) + gain automation lanes driven by the voice track's envelope.
