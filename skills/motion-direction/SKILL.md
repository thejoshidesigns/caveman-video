---
name: motion-direction
description: >
  Senior creative direction, motion physics, spatial staging, color science,
  and anti-slop taste calibration for video and motion graphics. Consolidates
  motion-art-direction, animation-principles, shot-composition, color-motion,
  and design-taste-frontend (taste-skill). Use before animating or designing
  cards, scenes, palettes, camera moves, or multi-aspect (16:9 / 9:16 / 4:5) layouts.
---

# Motion Direction, Physics, Staging & Color (`motion-direction`)

Define the motion language and visual direction **before** numbering a keyframe or writing a shader. Good direction is subtraction: deciding what NOT to move.

---

## 1. Brief Inference & Anti-Slop Taste Dials (`taste-skill`)

### The 3 Dials (Set in Strategy Gate)
- **`DESIGN_VARIANCE` (1–10):** `1` = strict symmetry, `10` = asymmetric editorial/experimental (Default: `7–8`).
- **`MOTION_INTENSITY` (1–10):** `1` = static, `10` = kinetic physics/whip-pans (Default: `6`).
- **`VISUAL_DENSITY` (1–10):** `1` = airy gallery negative space, `10` = dense HUD/audit data (Default: `3–4`).

| Brief Signal | VARIANCE | MOTION | DENSITY |
| :--- | :---: | :---: | :---: |
| Minimalist / Linear-style / B2B SaaS / Fintech | `5–6` | `3–4` | `2–3` |
| Premium Consumer / Apple-style / Brand Launch | `7–8` | `5–7` | `3–4` |
| Playful / Lifestyle / EdTech / Kinetic Social | `8–9` | `7–9` | `3–4` |
| Clinical / Audit / Data / Technical Explainer | `4–5` | `3–5` | `5–7` |

### Anti-Slop Discipline (Banned Defaults)
- **No Default AI-Purple/Neon Glow:** Do not use random neon purple/blue glows unless the brand's actual palette is lavender/violet (like *Hey Siya* `#A084E8` + Teal `#2CD3C0`, where it is locked to real brand tokens).
- **Serif Discipline:** Default to crisp display sans (`Plus Jakarta Sans`, `Geist`, `Cabinet Grotesk`, `Satoshi`, `SF Pro Display`). Never default to `Fraunces` or `Instrument Serif`. For emphasis inside a headline, use **bold or italic of the SAME font family**—never mix a random serif word into a sans headline.
- **Italic Descender Clearance:** When using italic display type containing `y, g, j, p, q`, enforce `line-height >= 1.15` and bottom padding so descenders never clip.

---

## 2. Tone Matrix & Named Motion Personalities (`motion-art-direction`)

Place every video on the **2×2 Tone Matrix** and lock **ONE Motion Personality** for the entire piece:

| Personality | Matrix Cell | Base Duration | Signature Easing Curve | Overshoot | Reads As |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Premium** | Calm × Soft | `350–600ms` | `cubic-bezier(0.22, 1, 0.36, 1)` or `(0.4, 0, 0.2, 1)` | `0%` | Elegant, minimal, luxury |
| **Corporate** | Calm × Sharp | `200–400ms` | `cubic-bezier(0.2, 0, 0, 1)` | `0–3%` | Clean, trustworthy, B2B/EdTech |
| **Playful** | Kinetic × Soft | `150–300ms` | `cubic-bezier(0.34, 1.56, 0.64, 1)` (`back.out`) | `10–20%` | Bouncy, friendly, lifestyle |
| **Energetic** | Kinetic × Sharp | `100–250ms` | `cubic-bezier(0.16, 1, 0.3, 1)` (`expo.out`) | `15–30%` | Bold, hype, fast social |

### Restraint Checklist (What NOT to Animate)
- Never animate the entire frame at once.
- Never transition a transition (no simultaneous spin + wipe + fade).
- Never loop-animate text the viewer is actively reading.
- Hold stillness $\ge 0.3\text{s}$ (and $\ge 1.0\text{s}$ on final card state before cut) so the eye absorbs the takeaway.

---

## 3. Animation Physics & Easing (`animation-principles`)

### The Three Motion Layers (Projected onto Depth)
| Layer | Role | Parallax Speed | Opacity / Contrast | Motion Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Primary (Hero)** | The 1 thing the shot is about | `1.0–1.5x` | `1.0` (Full contrast) | Boldest move; lands on the beat or payoff word |
| **Secondary (Support)** | Supporting context / labels / badges | `0.5–0.7x` | `0.6–0.85` | Smaller, faster, settles `40–80ms` after Hero |
| **Ambient (Texture)** | Background mesh, grain, subtle drift | `0.1–0.3x` | `0.08–0.25` | Slow periodic loop (`8–24s`); never steals focus |

### Universal Easing & Timing Rules
- **Enter / Appear:** `cubic-bezier(0.22, 1, 0.36, 1)` or `cubic-bezier(0.16, 1, 0.3, 1)` (`300–500ms`). Fast launch, soft landing.
- **Exit / Disappear:** `cubic-bezier(0.4, 0, 1, 1)` or `cubic-bezier(0.7, 0, 0.84, 0)` (`200–300ms`).
- **On-Screen Move / Camera:** `cubic-bezier(0.65, 0, 0.35, 1)` (`300–400ms` UI, `800–2000ms` camera push).
- **Stagger Timing:** `40–80ms` per list item (`20–40ms` for dense grids); cap total group reveal at `600–800ms`.
- **Payoff-Word Sync:** When an overlay accompanies narration, start the reveal `reveal_duration` seconds *before* the spoken payoff word so the final settled frame lands **on** the keyword.
- **Typing / Counter Anchor Trick:** Always center/layout against the **full final string width**, never the partial string width (prevents horizontal sliding during typing/counting).

---

## 4. Spatial Staging, Grids & Multi-Aspect Safe Areas (`shot-composition`)

1. **Grid & Baseline:**
   - Landscape `1920×1080`: 12 columns, outer margin `80–120px`, gutter `24–32px`, `8px` vertical baseline unit.
   - Place the primary focal point on a **Rule-of-Thirds power intersection** (`33%` or `67%`), not dead-center (unless deliberate formal symmetry).
   - Rank visual hierarchy strictly: **Size > Contrast > Color > Position**.
2. **The 1/3 Rule (Two Forms):**
   - *Spatial Distance:* No element travels $>1/3$ of the canvas in an unbroken slide without a scale/opacity change or intermediate keyframe.
   - *Simultaneity:* Keep $\le 1/3$ of elements in active motion simultaneously.
3. **One Camera Move Per Beat:** Push/pull OR pan OR parallax—never stack push + pan + rotation together.
4. **Multi-Aspect Safe Margins & Restacking:**
   - **`16:9` (`1920×1080`):** `5%` title-safe margin all sides (`96px` X, `54px` Y).
   - **`9:16` (`1080×1920`):** Top `12–14%` (`230px`), Bottom `18–20%` (`360px` — cleared for Reels/TikTok/Shorts UI), Sides `6%` (`64px`). **Scale typography up by $\times 1.3–1.4$** and **restack** horizontal side-by-side layouts vertically—never blind-crop `16:9`.
   - **`4:5` (`1080×1350`):** Sides `6%`, Top/Bottom `8%`. Derive vertical layout bounds from `9:16` by scaling $Y$ and $H$ by $1350 / 1920 \approx 0.703$.

---

## 5. Color Science, OKLCH Palettes & Rec.709 Management (`color-motion`)

1. **Restrained Palette Formula:**
   - **1 Primary + 1 Accent + 2–3 Tinted Neutrals.** Tint dark/light neutrals slightly toward the primary hue angle in `oklch(L C H)` so backgrounds never look like dead gray.
   - In dark scenes, make accents pop via **higher lightness (`L = 0.75–0.85`) and moderate chroma**, not 100% neon saturation.
2. **Perceptual Interpolation:**
   - Always interpolate gradients and color transitions in **OKLCH or Lab** (`linear-gradient(in oklch, ...)`), never raw sRGB (which passes through muddy gray midpoints).
   - Add `3–5%` subtle noise/grain or stacked radial mesh gradients to eliminate 8-bit gradient banding.
3. **The 5-Step Grading Order:**
   1. Exposure / White Balance → 2. Contrast (Black/White points) → 3. Midtones / Saturation → 4. Split-Tone (e.g., subtle teal shadows + warm orange/amber highlights, protecting skin tones) → 5. Unify (vignette/LUT).
4. **Rec.709 (`bt709`) vs. sRGB & QuickTime Gamma Bug:**
   - Always tag SDR video outputs explicitly on FFmpeg encode:
     ```bash
     -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709
     ```
   - Never judge contrast or skin tones in macOS QuickTime Player (applies ~1.96 gamma shift); verify via PNG contact sheets, Chrome, or DaVinci Resolve.
   - For transparent video overlays: **H.264 MP4 cannot store alpha** (renders black background). Use **raw RGBA pipe**, **ProRes 4444 (`prores_ks -profile:v 4444 -pix_fmt yuva444p10le`)**, **WebM VP9 alpha**, or **PNG sequence**.
