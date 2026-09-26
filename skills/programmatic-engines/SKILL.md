---
name: programmatic-engines
description: >
  Code-driven deterministic video and animation engines: Remotion (React),
  HyperFrames (HTML/CSS/GSAP/WebGL), Manim Community Edition (3Blue1Brown math
  & algorithms), Motion (motion/react & CSS linear() springs), and Adobe After
  Effects (expressions, rigging, .mogrt, Render Queue vs AME, .jsx ExtendScript).
  Consolidates remotion-video, hyperframes-*, manim-video, motion, and after-effects.
---

# Programmatic Video & Animation Engines (`programmatic-engines`)

Every frame must be a deterministic function of time/frame index. Never use `Math.random()`, `Date.now()`, `performance.now()`, or untracked `setTimeout` inside a video render.

---

## 1. Parallel Slot Architecture (`video-use` Hard Rule 10)

When building multiple standalone animations to composite into an edit:
1. Isolate each animation inside `<videos_dir>/edit/animations/slot_<id>/`.
2. **Spawn parallel subagents (`cavecrew-animator`)** — one subagent per slot, running simultaneously so wall-clock time equals the slowest single slot.
3. Each slot outputs `edit/animations/slot_<id>/render.mp4` (or `render.webm` / ProRes 4444 with alpha) and verifies exact duration/dimensions with `ffprobe`.

---

## 2. Remotion (`remotion-video`)

Use when React component state, Zod-typed parametric templates, or `@remotion/three` is the cleanest authoring model.

### Core Rules
- **Frame-Driven Only:** Derive all motion from `const frame = useCurrentFrame()` and `const {fps, durationInFrames, width, height} = useVideoConfig()`.
- **Always Clamp `interpolate`:**
  ```tsx
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  ```
- **Springs:** `spring({frame, fps, config: {damping: 200, mass: 1, stiffness: 100}})`.
- **Scheduling:** Use `<Sequence from={f} durationInFrames={d}>` (resets child `useCurrentFrame()` to `0`) or `<Series>` (with negative `offset` for crossfades).
- **Deterministic Randomness & Assets:** Use `random('seed-string')` from `remotion`, load local files with `staticFile()`, and gate async font/asset loads with `delayRender()` / `continueRender()`.
- **Offline Beat Sync:** Bake beat timestamp arrays (`const BEATS_SEC = [...]`) into props before rendering; headless rendering has no realtime Web Audio clock.

### Mandatory Verify Loop (Stills → Contact Sheet → Encode)
```bash
# 1. Render start / mid / end stills first (fast, no full encode)
npx remotion still Promo out/f-start.png --frame=0
npx remotion still Promo out/f-mid.png   --frame=75
npx remotion still Promo out/f-end.png   --frame=149

# 2. Tile & inspect contact sheet for clipping / layout bugs
python3 <caveman-video>/helpers/contact_sheet.py out/f-start.png out/f-mid.png out/f-end.png -o out/verify_sheet.png

# 3. Encode full MP4 only after stills pass
npx remotion render Promo out/promo.mp4
```

---

## 3. HyperFrames (`hyperframes-core`, `-animation`, `-keyframes`, `-cli`)

Use for browser-native HTML/CSS/GSAP video compositions, website/UI motion captures, and Registry shader treatments.

### Non-Negotiable Authoring Contract (`hyperframes-core` & `-animation`)
1. **Single Paused Seekable Timeline:** Register timelines on `window.__timelines` (paused by default). `data-duration` on the root composition governs length.
2. **No Layout Thrashing in Tweens:** Animate GSAP transform aliases (`x`, `y`, `scale`, `rotation`, `opacity`, `autoAlpha`)—never `top`, `left`, `width`, `height`, or `display`.
3. **Pre-Calculate Layout Coordinates:** Never call `getBoundingClientRect()` inside a tween callback (parallel frame workers will desync). Compute once at setup.
4. **No `repeat: -1` or Page-Load `gsap.set` on Later Clips:** Keep clip visibility owned by `data-start` and `data-duration`.

### CLI Workflow (`hyperframes-cli`)
```bash
export PRODUCER_BROWSER_GPU_MODE=hardware
npx --yes hyperframes init . --example blank --non-interactive --skip-skills
npx --yes hyperframes lint
npx --yes hyperframes check
npx --yes hyperframes render . -o render.mp4
```

---

## 4. Manim Community Edition (`manim-video`)

Use for 3Blue1Brown-style mathematical proofs, equation derivations, algorithm visualizations, and formal state machines.

### Pedagogical & Visual Standards
1. **Geometry Before Algebra:** Show the geometric intuition/shape first, then introduce the `MathTex` equation.
2. **Opacity Salience Layering:** Primary active mobjects at `1.0`, contextual mobjects at `0.4`, structural axes/grids at `0.15`.
3. **Breathing Room:** Always call `self.wait(1.0–2.0)` after key reveals.
4. **Implementation Guardrails:**
   - **Monospace Font Only (`Menlo`):** Manim's Pango renderer breaks kerning on proportional fonts (`Text("Label", font="Menlo", font_size=24)`). Minimum `font_size=18`.
   - **Raw Strings for LaTeX:** Always `MathTex(r"\frac{1}{2}")`, never `"\frac{1}{2}"`.
   - **Edge Buffer:** Always `to_edge(DOWN, buff=0.5)` (never `< 0.5`).
   - **Clean Scene Exits:** `self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)` at scene end.

```bash
# Draft still preview -> Draft video -> Production 1080p60 render
manim -ql --format=png -s script.py Scene1_Intro
manim -qh script.py Scene1_Intro
```

---

## 5. After Effects & Web Motion (`after-effects` + `motion`)

### After Effects Expressions, Rigging & Export (`after-effects`)
- **Essential Expressions:**
  ```js
  // Timeless per-layer random seed + wiggle
  seedRandom(index, true);
  wiggle(2, 30);

  // Staggered leader-follower delay
  thisComp.layer("Lead").transform.position.valueAtTime(time - 0.08 * index);

  // Inertial bounce on keyframes
  n = 0;
  if (numKeys > 0) {
    n = nearestKey(time).index;
    if (key(n).time > time) n--;
  }
  if (n == 0) { t = 0; } else { t = time - key(n).time; }
  if (n > 0 && t < 1) {
    v = velocityAtTime(key(n).time - thisComp.frameDuration/10);
    amp = .05; freq = 3.0; decay = 5.0;
    value + v*amp*Math.sin(freq*t*2*Math.PI)/Math.exp(decay*t);
  } else { value; }
  ```
- **Render Queue vs. Media Encoder:**
  - **Render Queue (RQ):** Use for **ProRes 422 HQ** (masters) and **ProRes 4444 with RGB + Alpha** (transparent overlays).
  - **Adobe Media Encoder (AME):** Use for **H.264 MP4** delivery (`10–16 Mbps` 1080p, `35–45 Mbps` 4K, tagged Rec.709). Never export transparent comps to H.264 (renders black bg).
- **ExtendScript (`.jsx`) Hygiene:** Wrap batch operations in `app.beginUndoGroup("Task") ... app.endUndoGroup()` and reference effects by `matchName` (`"ADBE Gaussian Blur 2"`).

### Web UI Animation (`motion`)
- Prefer `import { motion, useMotionValue, useTransform } from "motion/react"` (never mix `framer-motion` and `motion` in the same `package.json`).
- Never drive continuous scroll/pointer motion via React `useState` (causes 60fps re-render thrash); bind `useMotionValue` directly to `style`.
