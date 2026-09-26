---
name: screen-and-explainer
description: Automated browser walkthrough recording (Playwright/CDP + live interactive capture), macOS AVFoundation screen capture, and Screen-Studio-style post-production (spring-eased auto-zoom on clicks, cursor smoothing & click ripples, rounded macOS window chrome, UI spotlight cutouts, keystroke HUD pills, and TTS step narration). Use whenever creating product demos, SaaS explainers, tutorial videos, or polishing screen recordings.
---

# `screen-and-explainer` — Browser Walkthroughs & Screen-Studio Explainer Engine

Turns either a **live URL / web app** or an **existing raw screen recording** into a polished, Screen-Studio-grade product explainer video with automatic camera pan/zoom on clicks, rounded macOS window chrome, cursor click ripples, UI spotlights, keystroke HUDs (`⌘ + K`), and synced voiceover.

---

## 1. Two Input Pipelines

### Pipeline A: Automated or Interactive Browser Capture (`helpers/record_browser.mjs`)
Use when the user gives a URL (`https://...` or `http://localhost:3000`) or asks to record a web app flow.
* **Scripted Mode (`--plan edit/walkthrough.json`)**: Drives Playwright in a crisp `1920×1080` (or `1080×1920`) viewport, moves the cursor along human cubic-bezier paths, types at natural human cadence (`55ms/char`), and outputs:
  1. `edit/raw_screen.mp4` (clean viewport capture)
  2. `edit/cursor_events.json` (frame-accurate timestamped log of every `move`, `click`, `type`, `scroll`, `keystroke`, and `spotlight` bounding box)
* **Interactive Mode (`--url <url> --interactive`)**: Opens a visible browser window, injects passive DOM listeners (`mousedown`, `mousemove`, `keydown`, `scroll`), and logs the human's exact clicks and keystrokes into `edit/cursor_events.json` while recording the viewport.

```bash
# Scripted browser walkthrough -> raw_screen.mp4 + cursor_events.json
node helpers/record_browser.mjs --plan edit/walkthrough.json -o edit/raw_screen.mp4

# Interactive browser recording (30s max or until window closed)
node helpers/record_browser.mjs --url http://localhost:3000 --interactive -o edit/raw_screen.mp4
```

### Pipeline B: Native macOS Screen / Window Capture (`avfoundation`)
Use when capturing a native macOS desktop app, terminal, or simulator:
```bash
# 1. List screen & audio capture device indices (shrunk)
ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | grep -E "\[[0-9]+\]"

# 2. Capture screen index 1 at 60fps lossless CRF 14
ffmpeg -hide_banner -loglevel error -f avfoundation -framerate 60 -capture_cursor 1 -capture_mouse_clicks 1 \
  -i "1:none" -c:v libx264 -preset ultrafast -crf 14 -pix_fmt yuv420p edit/raw_screen.mp4
```

---

## 2. Walkthrough & Cursor Telemetry Schema (`edit/cursor_events.json`)

Whether generated automatically by `record_browser.mjs` or authored manually for an existing screen recording, `edit/cursor_events.json` drives the camera rig:

```json
{
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "windowTitle": "app.yourdomain.com — Dashboard",
  "events": [
    {
      "t": 1.20,
      "duration": 2.40,
      "type": "click",
      "x": 1420,
      "y": 180,
      "zoom": 1.85,
      "label": "STEP 01 // CREATE WORKSPACE",
      "sublabel": "Click New Project in the top-right toolbar"
    },
    {
      "t": 4.10,
      "duration": 1.80,
      "type": "keystroke",
      "x": 960,
      "y": 420,
      "zoom": 2.0,
      "keys": "⌘ + K",
      "label": "OPEN COMMAND PALETTE"
    },
    {
      "t": 6.50,
      "duration": 2.50,
      "type": "spotlight",
      "x": 480,
      "y": 320,
      "w": 620,
      "h": 280,
      "zoom": 1.55,
      "label": "REAL-TIME TELEMETRY"
    }
  ]
}
```

---

## 3. Screen-Studio Auto-Zoom & Polish Rules (Hard Rules)

1. **Click Clustering (Anti-Seasick Rule):**
   * NEVER zoom in and out on back-to-back clicks separated by `< 2.0s`.
   * Cluster consecutive clicks within `2.0s` into a **single sustained zoom hold**, smoothly panning `(cx, cy)` between targets while maintaining zoom level, then zoom out to `1.0x` only when interaction pauses for `> 1.8s`.
2. **Spring Camera Physics:**
   * **Zoom-In / Pan Curve:** `cubic-bezier(0.16, 1, 0.3, 1)` over `0.55s` (fast physical snap, long smooth settle).
   * **Zoom-Out Curve:** `cubic-bezier(0.4, 0, 0.2, 1)` over `0.65s`.
   * **Max Zoom Bounds:** Clamp zoom between `1.0x` and `2.35x`. Clamp camera center `(cx, cy)` so the zoomed viewport NEVER reveals out-of-bounds edges (`cx ∈ [W/(2*zoom), W - W/(2*zoom)]`).
3. **macOS Window Chrome & Ambient Stage:**
   * Wrap raw screen footage inside a padded studio canvas (`48px–72px` margin on `1920×1080`) with rounded corners (`radius: 20px`), a `36px` dark translucent macOS title bar with traffic lights (`#FF5F56`, `#FFBD2E`, `#27C93F`), a `1.5px` specular border (`rgba(255,255,255,0.14)`), and a deep drop shadow (`blur: 42px`, `alpha: 0.55`).
4. **Click Ripples & Keystroke HUDs:**
   * At each `type == "click"`, render an expanding concentric ring (`r: 8px -> 54px` over `0.45s`, fading alpha `0.85 -> 0.0`) plus a crisp vector pointer.
   * At each `type == "keystroke"`, render a centered bottom glass pill (`⌘ + K`) with spring pop-in (`cubic-bezier(0.34, 1.56, 0.64, 1)`).
5. **UI Spotlight Cutouts (`type == "spotlight"`):**
   * Dim the surrounding screen (`rgba(8, 12, 16, 0.62)`) while keeping the target rounded rectangle `(x, y, w, h)` at `100%` brightness with a glowing `2px` accent stroke.
6. **Speed-Ramping Dead Air:**
   * Any waiting/loading interval `> 2.2s` with no voiceover or cursor activity should be trimmed or speed-ramped (`2.5x–4x`) before running the compositor.

---

## 4. Rendering via `helpers/render_screen_studio.py`

`helpers/render_screen_studio.py` compiles a native macOS Objective-C / CoreGraphics Screen-Studio compositor on the fly and pipes `raw_screen.mp4` + `cursor_events.json` at `60+ fps` directly into `ffmpeg`.

```bash
# 1. MANDATORY PREVIEW GATE (Rule #9): Dump keyframe PNGs at each click/zoom event
python3 helpers/render_screen_studio.py edit/raw_screen.mp4 \
  --events edit/cursor_events.json --preview

# 2. Inspect edit/preview_frames/*.png with view_file to verify zoom framing & HUD placement

# 3. Full 60fps/30fps render with BT.709 color tags & -14 LUFS audio
python3 helpers/render_screen_studio.py edit/raw_screen.mp4 \
  --events edit/cursor_events.json -o output_explainer.mp4
```
