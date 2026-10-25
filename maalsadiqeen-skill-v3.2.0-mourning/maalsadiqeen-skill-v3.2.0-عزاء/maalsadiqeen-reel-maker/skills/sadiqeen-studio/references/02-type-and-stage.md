# 2 · Type and stage — the part that is easy to get wrong

This file is the studio's memory of four bugs and one design rule. Read it before you change
anything in `typo.py` or `stage.py`.

## 2.1 Why not Pillow's text renderer

`ImageDraw.text` uses libraqm when Pillow is built with it. Most sandboxes are not, and then
Arabic comes out **unjoined and left-to-right**, and no amount of `arabic-reshaper` fixes the
metrics (reshaper + bidi gives you connected letters, but the *widths* are wrong by a few percent
per word, which is enough to break a fitted line).

So: **HarfBuzz shapes, FreeType rasterises.** HarfBuzz is the same engine libass and Chrome use,
so a word measures the same here as it will on the phone.

```
text → split_runs() → _pieces() → hb.shape() → [gid, xadv, xoff, yoff]
     → _rasterise()  → FreeType bitmap per glyph onto an L canvas at 2× → LANCZOS down
     → _tint()       → RGBA in the token colour
```

## 2.2 The four traps

**1 · Units.** `face.set_char_size(px*64)` assumes 64 dpi and gives you glyphs at `px·72/64`,
while HarfBuzz advances are at `px`. The mismatch is invisible on one glyph and a broken join on a
line. Use `face.set_pixel_sizes(0, px*SS)` — always — and keep advancing in supersampled space,
rounding once per glyph:

```python
canvas.paste(glyph, (int(round(cursor + g.xoff)) + left, baseline - top - int(round(g.yoff))))
cursor += g.xadv          # never round the advance itself
```

**2 · The font's box is not the ink.** Amiri Quran reports ascender 349 / descender −122 per
1000 upem: a one-word layout is 584 px tall for 96 px of type. Centre a block on that and it
drifts 100 px high. `layout()` therefore **crops to its ink** and returns a baseline measured from
the top of the crop; `stack()`/`paragraph()` lay lines out on a baseline grid (`px × leading`)
and centre each crop inside its slot. If you add a block, use `Ink.baseline`, never `height/2`.

**3 · Missing glyphs are silent.** No installed Arabic font carries Latin punctuation: Noto
Kufi and Naskh have no `/`, `·`, `«`, `»`, `:` — and none of them has `﴿ ﴾` (U+FD3E/FD3F).
A missing glyph draws as tofu, not as an error. Two defences:

- `_pieces()` splits every run by the face's coverage table and falls back to Amiri for the
  characters the face does not have (each glyph remembers which face drew it);
- the verse brackets are **drawn** (`stage.flourish`) around the label, never typed.

**4 · Run order.** Arabic reads right to left, so the first logical run must be painted at the
*right* edge. `_rasterise` reverses the run list before painting left-to-right; without that, a
leading «—» in an attribution ends up above the last word. Test with
`typo.layout('— العلّامة المجلسي · مرآة العقول')` and look at it.

## 2.3 Fitting rules

| need | function | rule |
|---|---|---|
| one line that must stay one line | `fit(text, font, 800, hi, lo)` | largest size ≤ hi that fits 800 px, never below lo |
| a hero word | `fit(..., hi=138, lo=56)` | the hero is 110–138 px, one per reel |
| a passage | `fit_wrapped(...)` + `paragraph(...)` | ≤ 6 lines, ≤ 980 px tall, right-aligned |
| a verse | per-line `fit` on the widest line | one size for the whole āyah |
| anything that still does not fit | **cut words** | never below the block's `lo` |

Column: `x 150 → 950` (800 px), optical centre `CX = 550`, `OPTICAL_Y = 885`. Safe zone for
platform UI: `y 300 → 1440`. Nothing text-bearing above 300 or below 1440 — the caption overlay
and the Reels header live there.

## 2.4 The stage, top to bottom

| layer | what | note |
|---|---|---|
| paper | radial cream `#f4efe6→#ddd4c3` + fibre noise | charcoal `#171814→#060706` in mourning |
| plates | 8 pre-rendered vignette+grain plates, cycled | per-frame noise is slower and no better |
| light sweep | one soft diagonal band, one pass per 11 s | windowed alpha; cream palette ×0.28 |
| arc divider | 800×130 green hairline + three diamonds, breathes ±3 px / 7 s | the page's signature |
| sprig | drawn olive sprig, top-right, ±2.5 px / 5.5 s | `stage.sprig` |
| watermark | the tree logo at 20 % (ivory duotone on charcoal), from scene 2 to the last cut | never on the card |
| content | the blocks | one idea per frame |
| camera | total 0.8 % push over the reel | enough to feel alive, not enough to see |

Rules: **no red**, no pure black/white, no drop shadow, no glow except a wide, faint gold halo
behind a hero (alpha ≤ 0.28). Greens are ink; gold is a line, not a fill.

## 2.5 Motion vocabulary

| motion | value | where |
|---|---|---|
| entrance | `out3`, 0.5–0.9 s, `dy +14…30`, blur 5–12 → 0 | every text element |
| exit | `in2`, 0.42 s, `dy −20`, blur 4 (collective on the cut) | every text element |
| wipe | `out3` 0.6–0.95 s, from the right edge, pinned right | hero, quote, verse rule |
| strike | gold bar scaleX from the right, 0.45 s | `contrast.wrong` |
| seal | scale 1.5 → 1 with a blurred flash, 0.42 s | `proof.seal` |
| push | 0.8 % per second on the hero only | `answer`, `quote.hero` |
| breathing | ±2.5–3 px, 5.5–7 s, `sine` | arc, sprig |

Hierarchy inside a block: label → text → emphasis → attribution. Attribution always last. A
frame is never 100 % static, and it is never busy either: if two things move, one of them is
decorative and slow.

## 2.6 What makes a frame look amateur (the checklist)

- centred paragraphs — Arabic enters a line from the right, so centring makes the edge wander;
- a second hero, or a hero at the top of the frame instead of 50–65 %;
- type under 28 px anywhere (it is invisible on a phone);
- the watermark behind the closing card;
- three text sizes competing — the brand allows three per frame, and two is better;
- a gold fill where a hairline belongs;
- a halo so strong it reads as a glow;
- a line that touches the safe-zone edge: the platform UI will crop it.
