<div align="center">

# 🪨🎬 caveman-video — why use many token when few frame do trick

**Your AI video agent reads 50,000-token `ffprobe` dumps, 10,000-line Whisper JSONs, and writes 500 words of fluff before cutting a single frame. `caveman-video` make it stop.**

[![Works with 30+ Agents](https://img.shields.io/badge/works_with-Antigravity_·_Claude_·_Cursor_·_Codex-orange?style=flat-square)](#quick-start)
[![5 Render Engines](https://img.shields.io/badge/engines-Native_CoreGraphics_·_FFmpeg_·_HyperFrames_·_Remotion_·_Manim-blue?style=flat-square)](#the-5-engines)
[![NLE Export](https://img.shields.io/badge/NLE_Export-FCPXML_·_DaVinci_Resolve_·_Premiere_·_OTIO-green?style=flat-square)](#nle-timeline-export)
[![Skills Consolidated](https://img.shields.io/badge/skills_bundled-25_→_7_progressive_packs-purple?style=flat-square)](#the-7-skill-packs)

⚡ **One command install:** `node bin/install.js --global`

</div>

---

## 🪨 See It

<table>
<tr>
<th width="50%">🗣️ Normal video agent · 142 tokens + 48,000 input tokens</th>
<th width="50%">🪨🎬 Caveman-Video agent · 29 tokens + 3,200 input tokens</th>
</tr>
<tr>
<td valign="top">

> I have analyzed your `ffprobe` output and the full Whisper JSON transcript. The reason your captions are hidden behind the lower-third graphic card at 00:28.76 is because the `subtitles` filter was placed before the `overlay` filter in your FFmpeg filtergraph, and your audio has a clicking sound because there are no audio fades applied at the segment boundaries. I would recommend moving the subtitles filter to the end of the chain and adding a 30ms `afade` filter.

</td>
<td valign="top">

> `00:28.76`: 🔴 Rule 1 violation — overlay hides caption. Put `subtitles` LAST in filter chain. Add 30ms `afade` (`st=0:d=0.03`) per segment to kill cut pop.

</td>
</tr>
</table>

Same diagnosis. Same frame-exact fix. **80% fewer output tokens. 90% fewer input tokens.**
Timecodes (`00:28.76`), FFmpeg filtergraphs, cubic-bezier curves (`cubic-bezier(0.22, 1, 0.36, 1)`), OKLCH/hex colors, and file paths **never** get cavemanned. Only the prose around them dies.

---

## 🌍 Why This Exists

Video editing with AI agents suffers from two massive bottlenecks:
1. **Input Token Explosion (Reading Too Much):** A single `ffprobe` dump, a 30-minute word-level Whisper/Scribe JSON transcript, an FFmpeg progress log (`frame= 1420 fps= 60...`), or inspecting 20 individual full-res PNG frames burns **50,000–200,000 tokens per turn**.
2. **Domain Craft & Precision Gap (Writing Too Much Fluff, Missing Hard Rules):** General LLMs hallucinate FFmpeg flags, cut mid-word, forget 30ms audio fades (causing clicks), use robotic `linear` easing, blind-crop `16:9` into `9:16`, or bake washed-out sRGB gamma instead of `bt709`.

**`caveman-video` solves both ends** by combining [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)'s token-shrinking architecture with **25 production video, motion-graphics, audio, and NLE timeline skills**:

* **The 7 Progressive Skill Packs (`skills/`):** Distills 25 specialized skills (`video-use`, `talking-head-recut`, `motion-art-direction`, `animation-principles`, `shot-composition`, `beat-sync-editing`, `color-motion`, `motion-background`, `logo-animation`, `remotion-video`, `hyperframes-*`, `media-use`, `manim-video`, `lyrics-to-video`, `screenplay-storyboards`, `after-effects`, `taste-skill`, and the **Hey Siya** native macOS CoreGraphics/CoreText pipeline) into 7 lean, progressive-disclosure skills.
* **The `video-shrink` MCP Server (`src/mcp-servers/video-shrink/`):** Shrinks `ffprobe` JSONs by 95%, packs raw Whisper/Scribe word JSONs into phrase-level `takes_packed.md` + `captions.tsv` (1/10th the tokens), suppresses FFmpeg/Remotion frame-progress spam, and tiles preview keyframes into a single contact sheet PNG (cutting vision tokens by 90%).
* **The `cavecrew` Video Subagents (`agents/`):** `cavecrew-prober`, `cavecrew-director`, `cavecrew-animator`, and `cavecrew-qc`.

---

## ⚡ Quick Start

```bash
# Install globally into Antigravity (~/.agents/skills, ~/.gemini/config) and Claude Code (~/.claude/skills)
node bin/install.js --global

# Or install into the current workspace (.agents/skills)
node bin/install.js --workspace

# Check installation status
node bin/install.js --status
```

### Slash Commands
* `/caveman-video [lite|full|ultra|off]` — Toggle Caveman-Video terse mode & enforce the 15 Hard Rules.
* `/video-probe <dir_or_file>` — Run shrunk `ffprobe` inventory + cached Scribe/Whisper transcription → `edit/takes_packed.md` & `edit/captions.tsv`.
* `/video-recut <video>` — Package a talking-head / demo video with **Hey Siya**-style native CoreGraphics overlays or HyperFrames HTML/GSAP graphic cards.
* `/video-timeline <edl_or_storyboard.json>` — Export non-destructive `.fcpxml` (Final Cut Pro / DaVinci Resolve / Premiere Pro) and `.otio` timelines.
* `/video-qc <rendered.mp4>` — Run `--preview` contact sheet + `timeline_view.py` boundary waveform check + `ffprobe` verification.

---

## 📦 The 7 Skill Packs (`skills/`)

| Skill | Consolidates | What It Does |
| :--- | :--- | :--- |
| **`caveman-video`** | `caveman` + `video-use` (Core) | Master entry point: terse caveman prose rules, **5-Line Strategy Gate**, **15 Production Hard Rules**, and **5-Engine Router**. |
| **`cut-and-sync`** | `video-use` + `beat-sync-editing` + `lyrics-to-video` + `youtube-transcript` | Audio-first word-boundary cutting, 30–200ms padding, BPM-to-frame grid math (`(60/BPM)*fps`), `Establish → Develop → Climax → Resolve` pacing arc, J/L/match cuts, speed ramps, and 2–3 visual cuts per musical interlude. |
| **`motion-direction`** | `motion-art-direction` + `animation-principles` + `shot-composition` + `color-motion` + `taste-skill` | Brief inference, Anti-Slop Taste Dials (`VARIANCE / MOTION / DENSITY`), Tone Matrix & 4 Personalities (`Playful`, `Premium`, `Corporate`, `Energetic`), 3 Motion Layers (`Hero / Support / Texture`), 1/3 Rule, 12-col & `9:16` safe-zone restacking, OKLCH palettes, and `bt709` color management. |
| **`native-and-recut-overlays`** | **Hey Siya** `render_siya.m` + `talking-head-recut` + `logo-animation` + `motion-background` | **Dual Overlay Engine:** (1) Native macOS Objective-C / CoreGraphics / CoreText RGBA pipe compositor (`render_*.m` → `ffmpeg`) with `--preview` stills, glass cards, dark hero intercuts, brand bug, and word-synced pill captions; (2) HyperFrames HTML/GSAP `data-anim` card recuts, SVG stroke draw-on logo stings, and seamless periodic backgrounds. |
| **`programmatic-engines`** | `remotion-video` + `hyperframes-*` + `manim-video` + `motion` + `after-effects` | Deterministic code-driven video: Remotion (`useCurrentFrame`, `interpolate`, `spring`, `remotion still` verify loop), HyperFrames (`window.__timelines`, `npx hyperframes check/render`), Manim CE (3Blue1Brown math/algorithms), `motion/react`, and After Effects expressions/`.mogrt`/`.jsx`. |
| **`audio-and-media-os`** | `media-use` + `hyperframes-audio` | One-verb asset resolution (`bgm`, `sfx`, `image`, `icon`, `logo`, `voice`, `grade`, `lut`), proactive Media Opportunity Scan, dynamic voiceover EQ carve (`400Hz / 1kHz / 1.6kHz`), 30ms cut `afade`s, and EBU R128 `-14 LUFS` loudness mastering. |
| **`timeline-and-storyboards`** | `screenplay-storyboards` + NLE Export | Non-destructive `.fcpxml` (DaVinci Resolve / Final Cut / Premiere) & `.otio` timeline generation + screenplay-to-16:9 monochrome triptych storyboard sheets (`3840×2160`) and `storyboards.pdf`. |

---

## ⚙️ The 5 Rendering Engines

1. **Native macOS CoreGraphics + CoreText Pipe (`helpers/templates/render_native_template.m`)** — Compiles in `0.5s` via `clang -O3 -framework Cocoa`. Pipes raw RGBA frames at `60–120+ fps` directly into `ffmpeg` with zero browser overhead, crisp Apple CoreText Unicode/Indic shaping, glassmorphic cards, full-screen intercuts, and `--preview` keyframe PNGs.
2. **HyperFrames (`npx hyperframes`)** — Browser-native deterministic HTML/CSS/GSAP video compositions, Web Audio `data-fx-carve`, and `talking-head-recut` card decks.
3. **Remotion (`npx remotion`)** — React/TypeScript compositions with Zod schemas, `@remotion/three`, and headless `remotion still` → `remotion render` verification.
4. **Manim Community Edition (`manim`)** — 3Blue1Brown-style mathematical, algorithmic, and system architecture animations.
5. **Surgical FFmpeg + NLE XML/OTIO (`helpers/render_edl.py` & `helpers/export_timeline.py`)** — Frame-accurate multi-take extraction, 30ms audio fades, lossless concat, and instant `.fcpxml` / `.otio` handoff to DaVinci Resolve, Premiere Pro, or Final Cut Pro.
