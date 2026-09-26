---
name: timeline-and-storyboards
description: >
  Export non-destructive NLE timelines (Final Cut Pro .fcpxml v1.10 for DaVinci
  Resolve, Final Cut Pro, and Premiere Pro, plus OpenTimelineIO .otio) from
  edl.json or storyboard.json, and convert screenplays into scene-indexed shot
  lists and 16:9 monochrome triptych storyboard sheets (storyboards.pdf).
  Consolidates screenplay-storyboards and NLE timeline export.
---

# NLE Timeline Export & Screenplay Storyboards (`timeline-and-storyboards`)

Deliver both **baked MP4 renders** and **non-destructive NLE timelines (`.fcpxml` / `.otio`)** so human editors can tweak cuts, graphic overlay tracks, and audio lanes inside DaVinci Resolve, Final Cut Pro, or Adobe Premiere Pro.

---

## 1. Non-Destructive NLE Timeline Export (`.fcpxml` & `.otio`)

Whenever you produce an `edit/edl.json` or `edit/storyboard.json`, run `helpers/export_timeline.py` to generate both `.fcpxml` and `.otio` alongside the rendered video:

```bash
python3 <caveman-video>/helpers/export_timeline.py \
  --input edit/edl.json \
  --fcpxml edit/timeline.fcpxml \
  --otio edit/timeline.otio
```

### Multi-Track NLE Mapping Rules
1. **Primary Storyline (Spine / Track V1 + A1):**
   - Sequential source video ranges (`source`, `start`, `end`) mapped to rational frame durations (`frameDuration="100/2500s"` for 25fps, `"1001/30000s"` for 29.97fps, `"100/3000s"` for 30fps).
   - **Never use floating-point seconds inside `.fcpxml`** — FCPXML requires exact rational fractions (`<num>/<den>s`) snapped to the sequence timebase, or DaVinci Resolve / Final Cut will reject the import with frame-boundary errors.
2. **Connected Overlay Lane (`lane="1"` / Track V2):**
   - Graphic cards, Remotion/HyperFrames overlay clips, or transparent ProRes 4444 stingers attached at `offset` = `start_in_output`.
3. **Connected BGM / SFX Lane (`lane="-1"` / Track A2):**
   - Music beds and sound effects placed with exact start offsets and gain adjustments.
4. **Markers & Beat Notes:**
   - Every `beat` and `reason` from `edl.json` is exported as a timeline `<marker>` so the editor sees the AI's cut rationale right on the NLE timeline.

---

## 2. Screenplay-to-Storyboard Pipeline (`screenplay-storyboards`)

When the user provides a script/screenplay (`.pdf`, `.docx`, `.fdx`, `.fountain`, or plain text) and wants camera coverage or visual storyboards:

### Step 1: Index the Script & Lock Continuity Bible
1. Inventory every scene in order (`S001`, `S002`, ...) with source page/line anchors, characters, location, and time of day in a **Scene Coverage Ledger**.
2. Design shot coverage per scene (`S001-SH001`, `S001-SH002`, ...): shot size (`WS`, `MS`, `CU`, `ECU`), camera angle/height, movement, subject blocking, screen direction (180-degree axis consistency), and editorial purpose.
3. Lock a **Character Continuity Bible** before generating any images.
4. Lock one shared art direction: **monochrome black graphite pencil and fine pen lines on white paper, with neutral gray shading only** (no color, sepia, or photorealism).

### Step 2: Count, Estimate & Confirm Call Ceiling (`production_plan.json`)
- Group consecutive shots within each scene into **16:9 three-panel triptych sheets** (`ceil(scene_panels / 3)` sheets per scene):
  - **Panel 1 (Top Wide):** Establishing / wide framing.
  - **Panel 2 (Bottom-Left):** Medium / action beat.
  - **Panel 3 (Bottom-Right):** Close-up / reaction beat.
- Calculate total image-generation calls (`new character reference sheets + triptych sheets + max correction allowance`), record in `production_plan.json`, and **confirm with the user before the first image call**.

### Step 3: Generate, Inspect & Assemble `3840×2160` Sheets → `storyboards.pdf`
1. Generate canonical monochrome character reference portraits first; pass them in `ImagePaths` for every scene triptych to maintain visual identity.
2. Require **zero in-image text/captions** during generation; add crisp shot IDs (`S001-SH001`), camera notes, and action captions in a clean white footer outside the artwork when assembling each `3840×2160` 16:9 sheet.
3. Compile the Character Bible, Complete Shot List, and all 16:9 triptych sheets (1 sheet per landscape page) into `storyboards.pdf`.
