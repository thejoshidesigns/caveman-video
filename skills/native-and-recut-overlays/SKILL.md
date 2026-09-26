---
name: native-and-recut-overlays
description: >
  Package talking-head, interview, podcast, or product demo videos with timed
  motion-graphics cards, full-screen hero intercuts, persistent brand bugs,
  animated logos, ambient backgrounds, and word-synced pill captions. Supports
  two production engines: (A) Hey Siya Native macOS Objective-C / CoreGraphics /
  CoreText RGBA pipe renderer (60-120+ fps, zero browser overhead) and (B)
  HyperFrames HTML/CSS/GSAP talking-head-recut card decks. Consolidates Hey Siya
  pipeline, talking-head-recut, logo-animation, and motion-background.
---

# Native CoreGraphics & Talking-Head Recut Overlays (`native-and-recut-overlays`)

Dress up an existing talking-head or demo video with timed graphic cards, lower-thirds, data callouts, full-screen hero intercuts, brand stingers, and word-synced captions while the speaker footage plays cleanly underneath.

---

## 1. Engine Choice: Native macOS Pipe vs. HyperFrames HTML Deck

| Criterion | Engine A: Native macOS CoreGraphics Pipe (`render_*.m`) | Engine B: HyperFrames HTML/GSAP (`talking-head-recut`) |
| :--- | :--- | :--- |
| **Speed & Overhead** | **Fastest (`60–120+ fps`)** — compiles in `0.5s` via `clang`, pipes raw RGBA directly between two `ffmpeg` processes. Zero browser/Node/DOM overhead. | Headless Chromium capture via `npx hyperframes render` (`PRODUCER_BROWSER_GPU_MODE=hardware`). |
| **Best For** | **Hey Siya-style motion graphics edits**: glass cards, metric badges, full-screen dark intercuts, persistent brand bug, bottom progress bar, and word-synced pill captions (including Indic/Telugu/Unicode via CoreText). | 10-style HTML/CSS card decks (`warm-paper`, `clinical`, `experimental`) with split/stack/pip/overlay video-wrap tweening. |
| **Preview QC** | `./render_edit --preview` dumps 12–17 keyframe PNGs in `< 0.8s`. | `npx hyperframes snapshot` / `npx hyperframes preview`. |

---

## 2. Engine A: The Hey Siya Native macOS CoreGraphics Pipeline (`render_*.m`)

Start from `helpers/templates/render_native_template.m`. Copy it to `edit/render_edit.m` and customize scenes, brand palette, and assets.

### Step 1: Prepare Inputs in `edit/`
1. Probe video (`W`, `H`, `FPS`, `DURATION`).
2. Extract word-level timestamps (`edit/words_timed.txt` and phrase-grouped `edit/captions.tsv` via `helpers/pack_transcripts.py`).
3. Stage brand logos/mascots/icons into `edit/brand_assets/`.

### Step 2: Scene Choreography Pattern (Hybrid Overlays + Full Intercuts)
Structure `renderOverlayAtTime(double t)` in layers (respecting **Hard Rule 1: Captions LAST**):
1. **Persistent Brand Bug:** Drawn in top-left/top-right safe zone, automatically hidden during existing video logos or full-screen intercuts.
2. **Lower-Thirds & Side Callout Cards:** Drawn directly over the live speaker frame using `envelope(t, start, end, 0.38, 0.28)` (`easeOutQuint` enter, `easeInQuad` exit) with semi-transparent glass fill, subtle border, drop shadow, and staggered badges.
3. **Full-Screen Hero Intercuts:** At key structural beats (problem statement, architecture diagram, pricing/metrics, final outro CTA), draw a full-canvas dark/branded mesh background (`drawDarkHeroIntercutBackground`) that temporarily covers the speaker video while keeping the speaker's voiceover playing continuously.
4. **Word-Synced Editorial Pill Captions (Drawn LAST):**
   - Read phrase chunks + per-word start/end from `edit/captions.tsv`.
   - Render a translucent dark pill at `MarginV = 68px` from bottom; highlight the currently spoken word with an accent pill (`HEX_PRIMARY` / `HEX_ACCENT`) and bold text.
   - Automatically suppress captions during full-screen outro cards.
5. **Bottom Timeline Progress Bar:** `5px` gradient bar (`W * clamp01(t / duration)`) along the bottom edge.

### Step 3: Compile & Run `--preview` Contact Sheet First (Hard Rule 14)
```bash
# 1. Compile native renderer (0.5s)
clang -O3 -fobjc-arc \
  -framework Foundation -framework AppKit -framework CoreGraphics -framework CoreText \
  edit/render_edit.m -o edit/render_edit

# 2. Generate keyframe preview PNGs (<1s) and build 1 tiled contact sheet
./edit/render_edit --preview
python3 <caveman-video>/helpers/contact_sheet.py edit/preview_frames/*.png -o edit/preview_frames/contact_sheet.png
```
Inspect `edit/preview_frames/contact_sheet.png` once to verify zero text overflow, zero caption overlap, and clean typography.

### Step 4: Single-Pass Raw RGBA Pipe into FFmpeg (`bt709`)
```bash
ffmpeg -y -v warning -i "input.mp4" \
  -vf "scale=1920:1080,fps=25,format=rgba" -f rawvideo -pix_fmt rgba - \
| ./edit/render_edit \
| ffmpeg -y -v warning \
  -f rawvideo -pix_fmt rgba -s 1920x1080 -r 25 -i - \
  -i "input.mp4" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 192k -movflags +faststart \
  "final render/output_motion_edit.mp4"
```

---

## 3. Engine B: HyperFrames `talking-head-recut` Card Deck Pipeline

When using HTML/CSS/GSAP cards via `hyperframes`:

### Auto Card-Count Formula
Compute natural card rhythm from video duration and transcript information density (floor = **5 cards**, no upper clamp):
1. **Base Pace by Duration:**
   - `< 60s`: `6–8s/card` | `60s–3m`: `8–12s/card` | `3–10m`: `12–20s/card` | `10–30m`: `20–35s/card` | `> 30m`: `30–60s/card`
2. **Density Multiplier:**
   - **High density** (metrics, lists, rapid claims): $\times 0.7$
   - **Medium density** (mixed narrative + data): $\times 1.0$
   - **Low density** (single story, reflective): $\times 1.5$
3. **Formula:**
   $$\text{secPerCard} = \text{basePace} \times \text{densityMultiplier}, \quad \text{cardCount} = \max\left(5, \text{round}\left(\frac{\text{videoDurationSec}}{\text{secPerCard}}\right)\right)$$

### Layout × Style × Frame Matrix
| Layout | `card.zone` | Landscape `1920×1080` `#video-wrap` Bounds | Portrait `1080×1920` `#video-wrap` Bounds |
| :--- | :--- | :--- | :--- |
| **`split`** | `side-panel` | `{left: 960, top: 0, width: 960, height: 1080}` | `{left: 0, top: 960, width: 1080, height: 960}` |
| **`stack`** | `lower-third` | `{left: 14, top: 14, width: 1892, height: 548}` | `{left: 0, top: 0, width: 1080, height: 844}` |
| **`pip`** | `fullscreen` | `{left: 1480, top: 760, width: 400, height: 300}` | `{left: 690, top: 28, width: 360, height: 203}` |
| **`overlay`** | `video-overlay` | `{left: 0, top: 0, width: 1920, height: 1080}` | `{left: 0, top: 0, width: 1080, height: 1920}` |

- **3 Style Groups:** `warm-paper` (`academic`, `editorial`, `whiteboard`, `xhs` → `polaroid` frame), `clinical` (`audit`, `swiss`, `terminal`, `minimal` → `hairline` frame), `experimental` (`geom`, `spotlight` → `clean` frame).
- **Card HTML Contract:** Single root `<div class="card" data-card-id="{id}">`, all CSS rules scoped with `.card[data-card-id="{id}"]`, no `<script>` or external CDN URLs inside card fragments, transparent `.root` when sharing canvas with full-bleed video (`overlay`/`lower-third`), and portrait font sizes scaled $\times 1.3–1.4$.

---

## 4. Logo Animation & Ambient Motion Backgrounds (`logo-animation` + `motion-background`)

### Logo Stingers & Reveals (`0.8–2.5s`)
- **Pick ONE technique per logo:**
  1. *Stroke Draw-On:* SVG `<path pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">` animated to `0` over `1.1s cubic-bezier(0.65, 0, 0.35, 1)`.
  2. *Staggered Build-On:* Reveal container first → brand mark pieces (`stagger: 0.08, ease: "back.out(1.6)"`) → wordmark last.
  3. *Mask Wipe* or *Path Morph*.
- **Brand Integrity:** Never skew/squash brand geometry. Respect clearspace. Land the final settle frame (`scale 1.04 → 1.00` over `0.15s`) on the sonic logo peak. Always ship a static final-frame fallback.

### Seamless Looping Backgrounds
- Keep background contrast low (`Ambient` layer: `8–30s` period) so foreground text stays 100% legible.
- **Seamless Periodic Loop Math:** Wrap time $t$ into phase $\phi = \frac{t \bmod P}{P} \times 2\pi$ and drive offsets exclusively with $\sin(\phi)$ and $\cos(\phi)$ so frame $0$ and frame $P$ match byte-for-byte with zero loop jump.
