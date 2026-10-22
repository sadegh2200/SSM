# Motion & composition rules (HyperFrames + motion-design, as applied to this brand)

Everything here is already implemented in `build_reel.py`; read it when you extend a block, hand-edit
the generated `index.html`, or need to explain a choice.

## HyperFrames mechanics that matter

- Root `#root[data-composition-id="main"]` with `data-duration`; each scene is a `<section class="clip">`
  with `data-start`/`data-duration` and alternating `data-track-index` (keeps the lint quiet).
- One GSAP timeline `tl` (paused) registered as `window.__timelines["main"]`, built after
  `document.fonts.ready`, then `tl.seek(0)` and `window.__hfForceTimelineRebind()`.
- Background (`#bg`) and watermark live outside the clips so they persist across cuts.
- `<audio>` is one pre-mixed file (`assets/audio/mix.wav`); never layer several `<audio>` tags.
- `direction: rtl` is applied on `#root`/`.stage` only. **`<html dir="rtl">` renders a blank video.**
- Layering by DOM order; no negative z-index (lint). `isolation: isolate` for underline bars.
- Fonts are local `@font-face` TTFs; no CDN. GSAP is local `assets/gsap.min.js`.
- Check before render: `npx hyperframes check <project>`; snapshots: `npx hyperframes snapshot
  <project> --at t1,t2 -o <dir> --no-end` (there is no `--out`). Render: `--workers 1`.
- The nested-structure *warnings* («needs sub-composition») are expected and harmless here.

## The 12 principles, translated

| principle | how it shows up |
|---|---|
| Timing & spacing | entrances 0.6–0.95 s `power3.out`; exits 0.42 s `power2.in`; never linear except camera pushes |
| Anticipation | the hook underline draws *after* the word lands (+1.9 s); the riser 6 s before the hero |
| Staging | one idea per frame; the hero line alone at 50–65 % of the runtime |
| Follow-through | hero glow settles over 2.2 s after the wipe; seal flash decays 1.1 s |
| Slow-in/out | all eases are power curves; `sine.inOut` for breathing loops |
| Arcs | the arc divider breathes ±8 px; the plane enters on a curved path (x −140, y +90, −18°) |
| Secondary action | light sweep across the whole duration; sprig sway ±2°; verse 1.5 % slow scale |
| Exaggeration | restricted to the hero: 118 px, wipe + underline + glow + 2.8 % push |
| Appeal | paper, grain, vignette — the frame must look printable |

## Choreography

- Cuts happen on the beat of the audio event (`whoosh-short` on the cut). Reveals are 0.28 s *before*
  the audible/visual beat so the eye is ready.
- Hierarchy of reveals inside a scene: label → main text → emphasis → attribution. Attribution always last.
- Exits are collective (`.stage > *` together at `end − 0.45`) — the viewer should never watch items
  leave one by one.
- Hold rule: important text stays ≥ 1.8 s after its last word; the brand card ≥ 1.5 s.
- RTL: wipes go right→left (clip-path `inset(... 100%)` → `0%`), underline bars grow from the right,
  cards slide in from the right (`x +70`).

## Typography fitting

`fit()` measures the real shaped width of each line (Pillow + libraqm, within 1 % of Chrome) and
chooses the largest size under the block's cap that fits the 800 px column (780 px for the padded hero).
`fit_wrapped()` lets verses/quotes flow across ≤ 4 lines and caps total height at 980 px. If a line is
fitted below its minimum size the builder keeps the minimum — that is your cue to cut words.

## Snapshot discipline

Look at frames at: hook +1.2 s, verse highlight +0.9, strike +0.9, hero +0.9, seal/cards +0.9, final
+0.9, and every scene's `end − 0.8`. Check: nothing clipped by the stage padding, no word orphaned on
a line (except deliberately), gold emphasis present, watermark not overlapping text, brand card centred.
Only then render.
