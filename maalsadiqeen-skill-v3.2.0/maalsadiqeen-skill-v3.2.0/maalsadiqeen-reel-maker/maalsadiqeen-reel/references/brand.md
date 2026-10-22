# Brand system — «مع الصادقين» (@maalsadiqeen)

The page publishes dignified Arabic religious knowledge (Qurʾan, ḥadīth of the Ahl al-Bayt, scholarly
verification) for an educated Arabic-speaking audience.

> **Voice lives elsewhere.** Visual tokens are here; the *verbal* identity — promise, layers, lexicon,
> honorifics, honour code, the «الأثر في الحياة» block, the approved CTAs and the forbidden list — is
> `references/brand-voice.md`, and the reader is `references/audience.md`. `config/brand.json` is the
> machine-readable half of both. The video identity is a *moving version of the
paper sheets*: cream paper, dark green text, gold accents, a thin green arc with diamonds, an olive
sprig top-right, the tree logo. Nothing flashy; every motion must feel like ink settling on paper.

## Tokens (baked into `build_reel.py`'s CSS and into the Remotion template's `DEFAULT_PALETTE`)

| token | value | use |
|---|---|---|
| paper | `#ece6da` → radial `#f4efe6 / #ebe4d7 / #ddd4c3` | background, always |
| green | `#1f4a35` (text), `#2f6a4b` (light) | Qurʾan, ḥadīth, headlines |
| gold | `#957238`, `#cdb078` (gradient end) | emphasis word, underline, rule, seal ring, labels |
| ink | `#2d2b27`, ink-2 `#5a5650` | prose, attributions, labels |
| line | `#8aa58f` | arc divider |
| grain | SVG turbulence, opacity 0.085, multiply | paper texture |
| vignette | radial `rgba(70,52,28,0.17)` | edge focus |

Remotion template mapping: `green`, `gold`, `goldSoft`, `ink`, `inkSoft`, `olive` = the tokens above; the
warning-clause token `maroon` = deep gold-ink `#7a5a24` (emphasis without red).

Never introduce red, blue, pure black `#000` or pure white `#fff`; never use drop shadows or glows other
than the gold hero glow.

## Two palettes (`config/brand.json → themes`)

The page has one voice and two lights. Both are the same layout, type and motion; only the tokens change,
and the renderer picks them up from `spec.theme` (or `--theme`).

| | **main · النهار** | **mourning · ليلُ العزاء** |
|---|---|---|
| paper | `#ece6da` (cream) | `#0e0f0e` — warm charcoal, **not** `#000` |
| text | `#2d2b27` ink on cream | `#efe8d8` ivory on charcoal |
| sacred text (`.quran`, `.amiri`, `.kufi`) | `#1f4a35` green | `#e8dfcb` warm ivory |
| accent | `#957238` gold | `#c2a267` muted gold |
| body contrast | 11.4 : 1 | 15.7 : 1 |
| grain | multiply, 0.085 | screen, 0.06 |
| logo | unchanged | inverted to ivory (`filter: brightness(0) invert(1)`) |
| use | the default, every ordinary day | Muharram, Ṣafar, Ramadan nights, an anniversary of a death |

Rules for the dark palette:

- **No red.** Grief is not a warning colour, and blood-red is a different brand. The only warm tone is
  the muted gold.
- **No pure black and no pure white.** `#0e0f0e` and `#efe8d8` keep the paper feeling of the light
  theme; `#000` on `#fff` would look like a different page.
- The grain switches to `screen` so the dark surface keeps some texture instead of turning into plastic.
- Everything else — arc, sprig, gold rule, seal, typography — stays identical. The dark reel should
  read as the same page at night, not as a different account.

`verify.py` prints the theme and fails if the body contrast drops below 6 : 1 (it also warns if the gold
falls under 3 : 1, or if the mourning logo is left unfiltered).

## Typography

| class | font | role | size range (px, 1080 wide) |
|---|---|---|---|
| `.quran` | Amiri Quran | Qurʾanic text only (keeps the Uthmani marks legible) | 52–104 |
| `.amiri` (+bold) | Amiri | ḥadīth, scholar quotes, hero line | 46–118 |
| `.kufi` | Noto Kufi Arabic Bold | hook line, section headlines, CTA | 48–138 |
| `.kufi-r` | Noto Kufi Arabic Regular | small labels («بَلْ:», «﴿ سورة ﴾», share line) | 26–60 |
| `.naskh` | Noto Naskh Arabic | prose, cards, attributions | 26–52 |

Rules: full tashkeel on everything the viewer must *read as sacred or quoted* (verse, ḥadīth, hero
line, hook); attributions and references may drop tashkeel. Emphasis word → `<em>…</em>` in the spec
(renders gold at 1.18 em). One hero line per reel at ≥ 110 px. Max 3 text sizes per frame.

## Layout grid (1080×1920)

- Stage padding `0 130px 150px 150px` → text column 800 px wide, optical centre ≈ y 885.
- Arc divider: left 140 / top 285, 800×130 — stays for the whole reel except it fades at the CTA.
- Sprig: right 86 / top 236 (92×76). Watermark: centred, top 1372 (visible from scene 2 until the CTA).
- Safe zone for every platform UI: x 150–950, y 300–1440. The 4:5 feed crop is `crop=1080:1350:0:220`.
- Nothing text-bearing below y 1500 (Instagram caption overlay) or above y 250 (status bar / «Reels»).

## Motion personality (from the motion-design + HyperFrames skills, tuned for this brand)

- Entrances: `power3.out`, 0.6–0.95 s, from `y +22…40`, `blur 10–14px`, optional `scale 0.94–0.98`.
- Exits: `power2.in`, 0.42 s, to `y −22`, `blur 6px`, applied to the whole `.stage > *` at `end − 0.45`.
- Scene fade-in on `.stage` 0.35 s. No slide-in from left/right except the proof cards (`x +70`).
- Hero line: clip-path wipe from the right (RTL reading direction) 0.95 s + gold underline 0.6 s +
  gold glow 0.5 s then settling + 1.028 camera push over 3.6 s. Only once per reel.
- Continuous life: light sweep across the full duration, arc breathing ±8 px / 7 s, sprig ±2° / 5.5 s,
  verse/quote slow 1.5–2 % scale. A frame is never 100 % static.
- Strike-through: gold bar scaleX from right, 0.45 s `power2.inOut`, then the wrong phrase dims to 0.42.
- Seal: scale 1.55→1 with −9°→−5° rotation in 0.42 s + flash halo.

## Voice & tone of the on-screen copy (فصيح، متين)

- Short lines (2–6 words) in Classical Arabic; no colloquialisms, no exclamation marks, no emojis.
- Honorifics exactly: «عَلَيْهِ السَّلام» after an Imam's name on first mention, «(ع)» in attributions;
  «صلى الله عليه وآله» for the Prophet; «قال الله تعالى» / ﴿ ﴾ brackets for verses.
- Questions in the hook are allowed; sarcasm, polemics and naming opponents are not.
- Sources always with volume/page (ج/ص) in Arabic-Indic digits: «الكافي ج١ ص٢٠٨».
- Handle written `@maalsadiqeen` (Latin, lowercase) in the brand card and `maalsadiqeen` in the watermark.

## Audio identity

- No human narration by default (the owner rejects synthetic voices). Qurʾan recitation is welcome.
- Recitation: Maher al-Muaiqly (`ar.mahermuaiqly`) default, Alafasy alternative; raw, no reverb added.
- Bed: the deterministic D-minor pad from `gen_bed.py` at −7 dB, side-chain ducked under recitation.
- Sound design: paper-and-ink vocabulary — soft clicks on text, pen scratch on strike, sparkle on sacred
  lines, one bass impact on the hero, chime on the seal, whoosh on cuts, airy whoosh on the share plane.
- Master: −15.5 LUFS integrated (−14 if the client asks for "louder"), true peak ≤ −1.5 dBTP.
