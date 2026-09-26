---
name: cut-and-sync
description: >
  Audio-first cutting, multi-take EDL selection, beat-sync frame grid math,
  sequence pacing arcs, motivated transitions (J-cut, L-cut, match cut, whip pan,
  speed ramps), vocal-synced lyric videos with instrumental interlude cuts, and
  YouTube caption extraction. Consolidates video-use, beat-sync-editing,
  lyrics-to-video, and youtube-transcript.
---

# Cut & Sync (`cut-and-sync`)

Audio drives the cut; visuals follow. Snap every speech cut to a verbatim word boundary, and snap every musical cut to the cumulative BPM frame grid.

---

## 1. Transcription & Packed Transcript View (`video-use`)

1. **Cache Verbatim Word-Level ASR:**
   - Use ElevenLabs Scribe (`video-use/helpers/transcribe.py`) or local Whisper (`npx hyperframes transcribe <audio> --json --model small.en`).
   - Cache raw output in `edit/transcripts/<stem>.json`. **Never re-transcribe** an unchanged source file.
2. **Generate `takes_packed.md` & `captions.tsv`:**
   - Run `python3 <caveman-video>/helpers/pack_transcripts.py --edit-dir edit` to produce:
     - `edit/takes_packed.md`: Phrase-level lines broken on silence $\ge 0.5\text{s}$ or speaker change (`[002.52-005.36] S0 Text...`) at **1/10th the tokens** of raw JSON.
     - `edit/words_timed.txt` & `edit/captions.tsv`: Tab-separated `start\tend\tword` for frame-exact cuts and word-synced pill captions.
3. **YouTube Source Ingestion (when URL provided):**
   - For transcript-only research: `node Skills/youtube-transcript/scripts/youtube-captions.js "<url>" --timestamps`.

---

## 2. Speech Cut Craft & Multi-Take EDL Rules

### Cut Boundary Rules
- **Never cut inside a word.** Snap every `start` and `end` to exact word timestamps from `words_timed.txt` / `takes_packed.md`.
- **Cut Padding (Hard Rule 6):** Pad `30–200ms` around word boundaries to absorb ASR drift and breath:
  - Default talking-head / launch: **50ms pre-word**, **80ms post-word**.
  - Fast montage: **30–40ms**. Documentary / reflective: **120–200ms**.
- **Silence Gap Thresholds:**
  - $\ge 400\text{ms}$: Cleanest cut target.
  - $150–400\text{ms}$: Usable phrase boundary (verify with `timeline_view.py` for head-jerk).
  - $< 150\text{ms}$: Mid-phrase—unsafe to cut.
- **Speaker Handoffs & Reactions:** Leave `400–600ms` air on speaker changes. Extend cuts past `(laughs)`, `(sighs)`, and punchlines—the reaction IS the beat.

### Structural Archetypes for Multi-Take Assembly (`edl.json`)
Pick or adapt based on material:
- **Tech Launch / Product Demo:** `HOOK → PROBLEM → SOLUTION → PROOF/METRICS → EXAMPLE → CTA`
- **Tutorial:** `INTRO → SETUP → STEPS → GOTCHAS → RECAP`
- **Interview / Podcast:** `(QUESTION → ANSWER → FOLLOWUP/REACTION)` repeat
- **Documentary:** `THESIS → EVIDENCE → COUNTERPOINT → CONCLUSION`

```json
{
  "version": 1,
  "sources": {"C01": "/abs/path/C01.mp4"},
  "ranges": [
    {"source": "C01", "start": 2.42, "end": 6.85, "beat": "HOOK", "quote": "...", "reason": "Cleanest delivery"}
  ],
  "grade": "warm_cinematic",
  "overlays": [
    {"file": "edit/animations/slot_1/render.mp4", "start_in_output": 0.0, "duration": 5.0}
  ],
  "subtitles": "edit/master.srt",
  "total_duration_s": 87.4
}
```

---

## 3. Beat-Sync Editing & Rhythm Math (`beat-sync-editing`)

### Step 1: BPM → Cumulative Frame Grid
Never cut on every beat (causes viewer fatigue by beat 8) and never round `frames_per_beat` per-step (causes cumulative drift).

$$\text{frames\_per\_beat} = \frac{60}{\text{BPM}} \times \text{fps}$$

```js
// Frame-exact cumulative beat grid anchored to beat_1_offset_sec
const framesPerBeat = (60 / bpm) * fps;
const beatFrame = (beatIndex) =>
  Math.round((beat1OffsetSec * fps) + beatIndex * framesPerBeat);
```

- **Phrase Cutting:** Cut on **2, 4, or 8-beat phrases** (1 bar = 4 beats).
- **The Eighth-Grid:** Use $1/2$-beat (eighth) or $1/4$-beat (sixteenth) subdivisions sparingly for flash accents or transient SFX hits.
- **Land the Drop:** Place the single biggest visual reveal + speed-ramp impact on the musical drop frame.

### Step 2: Motion Personality → Cut Rhythm
| Personality | Cut Phrase | Transition Family | Retime Style |
| :--- | :--- | :--- | :--- |
| **Playful** | Every 4 beats + syncopated accents | Match cuts, quick whips | Light bouncy ramps |
| **Premium** | Every 8–16 beats (long holds) | Hard cut + rare dissolve | Slow, smooth ramps |
| **Corporate** | Every 8 beats (steady) | Clean hard cuts | Minimal retime |
| **Energetic** | Every 1–2 beats at climax | Hard cuts, whip pans | Aggressive beat speed-ramps |

### Step 3: Sequence Pacing Arc (`Establish → Develop → Climax → Resolve`)
Energy is the *derivative* of cut frequency. Never use uniform shot lengths:
1. **Establish:** `8–16 beats` per shot (longest holds, low tension, set mood).
2. **Develop:** `8 → 4 → 2 beats` per shot (shortening shots, rising tension).
3. **Climax:** `1–2 beats` per shot (fastest cuts + biggest visual + speed ramp on the drop).
4. **Resolve:** One long hold (release tension so logo/CTA breathes).

### Step 4: Motivated Transitions & Speed Ramps
Default to **hard cut** (90% of cuts). Use other transitions only when motivated:
- **Cut on Action:** Cut mid-movement (turn, hand gesture, transform peak) with matched velocity/direction so the seam is invisible.
- **Match Cut:** Outgoing and incoming frames share geometry, position, or motion vector (`1–2f` tolerance).
- **J-Cut (Audio Leads):** Next shot's audio starts `4–12 frames` before its picture. Pulls viewer forward into dialogue/reveals.
- **L-Cut (Audio Trails):** Current shot's audio continues `12–24 frames` under next shot's picture. Smooths scene transitions.
- **Speed Ramp (Impact Curve @ 30fps):**
  - `f00–f20`: `100%` speed (run-up)
  - `f20–f28`: Ease down to `25%` speed (slow-mo anticipation)
  - `f28`: **IMPACT lands on beat**
  - `f28–f40`: Snap/ease back to `100%` speed (release). Enable optical-flow/frame-blending if sub-50% speed strobes.

---

## 4. Lyrics-to-Video & Instrumental Interlude Rules (`lyrics-to-video`)

When building a lyric video, devotional video, or musical slideshow from an audio track:
1. **Separate Timeline into Vocal vs. Instrumental Segments:**
   - **Vocal Segments:** On-screen lyrics appear **strictly** during `[lyric_start, lyric_end]` while actively sung.
   - **Instrumental / Music Interlude Segments ($\ge 3.0\text{s}$):** Any intro, BGM interlude between verses (e.g., Pallavi/Charanam), or outro without vocals MUST be split into **2–3 distinct visual cuts** (`2.5–5.0s` each, synced to musical phrasing) with `"lyric": ""` (zero text on screen).
2. **Master Style Anchor:**
   - Define `style_anchor` once (medium, lens, lighting, palette, character continuity).
   - Generate `slide_01` first, then pass `slide_01` in `ImagePaths` for all subsequent vocal and interlude slides to lock visual identity.
3. **Ken Burns Camera Variety:**
   - Alternate `zoom_in`, `zoom_out`, `pan_left`, `pan_right` across consecutive slides so two identical camera moves never sit back-to-back.
4. **Multi-Script Typography (Indic / Telugu / Hindi / Tamil / English):**
   - Render burned lyrics LAST in the pipeline using Apple CoreText (native conjunct shaping, e.g., `Kohinoor Telugu Bold`) + pill background scrim (`pill_bg: true`), and normalize master audio to `-14 LUFS`.
