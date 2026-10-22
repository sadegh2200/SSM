# Remotion studio — the alternate engine (data-driven React template)

The default engine of this skill is HyperFrames (`SKILL.md`). Use this engine instead when:

- the sheets are a **ḥadīth + numbered traits + sanad chain** carousel (3–6 cards) — the template has
  purpose-built scenes for an animated rijāl chain with «ثقة» stamps, a verdict seal and progress chips;
- the user already has a Remotion studio (`~/reel-studio`) or asks for Remotion / React / Studio preview;
- HyperFrames cannot run on the machine (Node < 22, no Playwright browser) but Remotion can.

Same brand, same copy rules, same loudness target, same deliverables (`references/brand.md`,
`arabic-copy.md`, `publish.md` apply unchanged). Only the *data format* and the *scripts* differ:
you never edit React — you write `content.json` (what), `plan.py` turns it into `plan.json`
(when / how big), and the fixed template renders it. Iterate through JSON only.

```
cards (images) ──vision──▶ content.json ──validate──▶ 3 hooks scored ──plan.py──▶ plan.json
       ──extract_brand / make_audio──▶ render.py (stills → full) ──QA──▶ post_kit.py
```

## Contents

1. Preflight · 2. Intake → content.json · 3. Validate + hooks · 4. Plan · 5. Brand + audio ·
6. Render + QA · 7. Post kit · 8. Design tokens & layout · 9. QA checklist · 10. Fixing rules

## 1 · Preflight (once per machine)

```bash
source "$SKILL_DIR/scripts/env.sh"                                   # exports SKILL_DIR, REEL_WORK, REEL_DELIVER
python3 "$SKILL_DIR/scripts/setup_studio.py" --dest ~/reel-studio    # copies assets/remotion-template, npm install (remotion 4.0.535), Chrome, audio, tsc
#   reuse an existing install:  --link-node-modules /path/to/node_modules      skip steps: --skip-install --skip-browser
pip install -q imageio-ffmpeg opencv-python-headless numpy            # loudness probe · contact sheet · brand extraction
```

Low-memory machines (≈1 GB): render with `--concurrency 1` and never run Studio and a render together.
A 45 s render takes ≈3 min — run it in the background and keep working.

## 2 · Intake — read every card, then write `content.json`

Detect roles by content, not by position (the number and order of cards vary):

| card looks like | role | content.json |
|---|---|---|
| vocalised ḥadīth under an arc, «قال الإمام …», one-line thesis below | **hadith** (+ hook material, `hadith.bridge`) | `hadith.intro`, `hadith.lines[]`, `hadith.bridge` |
| numbered traits / conditions / meanings, 1–2 sentences each | **points** (2–5) | `points[]` |
| one supporting narration, tafsīr or scholar's explanation | **bayan** | `bayan` |
| narrator names with ثقة/ضعيف/إمامي… or «السند صحيح/معتبر» | **sanad** | `sanad.chain[]`, `sanad.verdict` |
| «المصادر»: book, volume, page | **sources** | `sources[]` (≤ 4, Arabic-Indic digits) |
| logo / handle / ornament corners | **brand** | `brand.handle`, `extract_brand.py` |

Typical layouts → scenes: **4 cards** (hadith · traits · sanad · sources) → hook · hadith · points · sanad · cta;
**3 cards** (hadith · explanation · sanad+sources) → hook · hadith · bayan · sanad · cta; **2 cards** → hook ·
hadith · sanad · cta (add `bayan` from the thesis if < 36 s); **5–6 cards** → expect `pace` warnings, move one
point into the caption. The sanad card is sometimes a footnote on the ḥadīth card and the chain lives in the
post caption — ask the user for it if it is on no card.

Transcription rules (the general rules in `content-analysis.md` also apply):

1. **Ḥadīth** — letter-for-letter with tashkeel; split at natural pauses («،» «؛», clause ends) into lines of
   ≤ 6 words / ≤ 42 letters, ≤ 10 lines (longer → two reels ١/٢). First clause `style:"lead"`; the
   consequence/exclusion clause («فليسَ منّا») `style:"warning"`. `intro` = the attribution as printed
   («قالَ الإمامُ الرضا عليه السلام:»), kunya as the card has it.
2. **Bridge** — the card's thesis line shortened to ≤ 5 words; omit if the card has none.
3. **Points** — only when the card enumerates. `title` = the ḥadīth's own phrase; `chip` = its one-word root
   (التسليم / الأخذ / المخالفة); `desc` ≤ 2 lines of ≤ 48 letters in the card's wording; a quoted supporting
   narration goes to `quote.lines` + `quote.src`.
4. **Bayan** — one block, ≤ 6 lines, the decisive line in `emphasis`.
5. **Sanad** — exactly as printed, author → Imam; grades verbatim (ثقة · ثقة جليل · إمامي ثقة · ممدوح · حسن ·
   مجهول · ضعيف · من مشايخ الإجازة); the Imam is the last node with `imam:true` and no grade; `verdict` is
   mandatory when a chain is shown and may never be more confident than the scholar's wording.
6. **Sources** — «الكتاب ج• ص•», Arabic-Indic digits («جلد: 27، صفحه: 116» → «ج٢٧ ص١١٦»).
7. **Honorifics** spelled out; **never** add explanation, numbers, dates or doctrine that is not on the cards.
8. `slug` = ASCII transliteration of the first 3–4 words; `title` = first clause without tashkeel.

Ask the user when: a word/grade/page is illegible · the chain is not on the cards · the verdict is nuanced
(معتبر vs صحيح, موثق, حسن) · > 10 ḥadīth lines or > 5 points (propose a split).

Schema and a generated `plan.json` are documented in `remotion-schema.md`; `assets/examples/shiatuna/`
(4 cards, 46 s) and `assets/examples/variant-bayan/` (3 cards, 42 s — layout fixture, verify its text before
publishing) are complete working inputs.

## 3 · Validate, then write and score three hooks

```bash
python3 "$SKILL_DIR/scripts/validate_content.py" jobs/<slug>/content.json --public ~/reel-studio/public
python3 "$SKILL_DIR/scripts/hook_score_ar.py" "hook A" "hook B" "hook C" --out jobs/<slug>/hooks.json
```

Fix every ERROR (emoji, colloquial, Persian-only letters, missing verdict, > 10 lines); warnings are layout
advice. Hooks: formulas and the three-hook routine in `hooks-ar.md`; the best (≥ 65, ideally ≥ 80) becomes
`hook.line1/line2`, the key word `hook.highlight`, the Imam's name `hook.sub`. Show all three to the user at
the end — hooks are what they most often want to change.

## 4 · Plan timing, pagination and type sizes

```bash
python3 "$SKILL_DIR/scripts/plan.py" jobs/<slug>/content.json --target 46     # hard limits 30–60 s
```

`plan.py` uses on-screen Arabic reading speed (≈ 2.3 words/s), paginates long ḥadīths («تتمّةُ الحديث»),
shrinks sanad rows for long chains (row = min(112, 800/N)), sizes type to the longest line, inserts 5-frame
crossfades and schedules every SFX cue. Read its summary: `pace` < 0.6 → too heavy (drop a point into the
caption or split); `pace` = 1.12 with total < 40 s → too light (add `bayan`, do not stretch holds). Targets:
42–48 s for hadith + points + sanad; 36–42 s for hadith + bayan + sanad. Never hand-edit frame numbers —
re-run `plan.py`.

## 5 · Brand and audio

```bash
python3 "$SKILL_DIR/scripts/extract_brand.py" cards/1.jpg --out ~/reel-studio/public      # logo.png, branch.png, brand.json
python3 "$SKILL_DIR/scripts/make_audio.py" --out ~/reel-studio/public/audio --plan jobs/<slug>/plan.json --maqam bayati
```

Look at the extracted PNGs; if the logo crop is wrong use `--logo-box br|tl|tr` or `--no-logo` (the frame falls
back to the `@handle` text). Keep the default palette (= `brand.md` tokens) unless the cards clearly use other
colours — then paste `brand.json → palette` into `content.brand.palette`.
The bed is a synthesised, non-rhythmic maqam drone at −20 dB RMS (religious audiences avoid percussive
music). A licensed nasheed/ambient track supplied by the user goes to `public/audio/pad.wav` at ≈ −20 dB RMS;
never download copyrighted audio.

## 6 · Render and QA

```bash
python3 "$SKILL_DIR/scripts/render.py" --studio ~/reel-studio --content jobs/<slug>/content.json --stills-only    # ≈20 s layout check
python3 "$SKILL_DIR/scripts/render.py" --studio ~/reel-studio --content jobs/<slug>/content.json --out "$REEL_DELIVER/<slug>"
```

Look at the stills and `contact-sheet.jpg` before declaring anything done (section 9). `qa.json` fails the run
on duration outside 30–60 s or a render error and warns on loudness outside −15.5 ± 2 LUFS / true peak
> −1.5 dBTP (the same mastering target as the default engine).

## 7 · Post kit and hand-off

```bash
python3 "$SKILL_DIR/scripts/post_kit.py" jobs/<slug>/content.json --hooks jobs/<slug>/hooks.json -o "$REEL_DELIVER/<slug>/post.md"
```

Deliver `<slug>.mp4`, `cover.jpg`, `contact-sheet.jpg`, `post.md` (caption, pinned chain comment, alt hooks,
publish checklist); keep `content.json` + `plan.json` for re-cuts. Summarise in Persian: structure, the three
hooks, and the two or three decisions the user may want to flip.

## 8 · Design tokens & layout (template `src/theme.tsx`, `src/ui.tsx`)

1080 × 1920, 30 fps, paper radial with 2 % grain; type and line-work only — no photos, faces or AI imagery.
`DEFAULT_PALETTE` carries the `brand.md` tokens (paper `#f4efe6→#ddd4c3`, green `#1f4a35`, gold `#957238`,
ink `#2d2b27`, olive `#8aa58f`); the `maroon` token (warning clause) is a deep gold-ink `#7a5a24` — the brand
never uses red. Any token can be overridden from `content.brand.palette`.

| role | font | plan key / size | notes |
|---|---|---|---|
| hook | Amiri Bold | `hook.size` 72–112 | highlight word green + underline draw-on |
| ḥadīth lead | Noto Naskh 700 | `hadith.lead` ≤ 128 | Noto keeps tashkeel attached at large sizes |
| ḥadīth body | Noto Naskh 500 | `hadith.body` 56–78 | line-height 1.75 |
| warning clause | Noto Naskh 700 `maroon` | `hadith.warning` ≤ 66 | 3 px underline over 24 frames |
| point title / desc | Amiri Bold green / Vazirmatn 400 | 72–104 / 34–44 | |
| sanad names | Vazirmatn 500 (Imam: Naskh 700) | `sanad.name` 30–40 | chips/stamps Vazirmatn 600 24–30 |
| CTA headline / sources | Amiri Bold green / Vazirmatn olive | 84–104 / 28–34 | |

Grid (y px): 0–250 and 1620–1920 are platform UI zones; logo bottom-left (y ≈ 1760), sprig top-right; hook
block centred with 70 px side padding; ḥadīth arc at 350, text from `page.top` (632), bridge at 1420; points
ring 500–520, title 660–690, chips 1430; sanad question 330, chain from 500 (row 112 → 72 for 11 nodes), note
1340; CTA sources 380, headline 700, footer 1400. Hook frame must survive the 4:5 centre crop (cover).

Motion: reveal = fade + rise 14–30 px (+ scale 1.04–1.07), 16–22 frames, `Easing.bezier(0.16,1,0.3,1)`;
5-frame scene overlap, 10–12 frame fade-out, CTA 34-frame fade to paper (clean loop); seal scale 1.6→1 with
overshoot, −7°→−4°, paper flash 0.35→0 over 16 f while the chain recedes (blur 3 px, 0.18 opacity); progress
chips pop 0.9→1 over 16 f. Nothing moves continuously except the soft icon pulse in the CTA.

Remotion rules the template already follows (keep them when touching it): duration/fps come from
`calculateMetadata` reading `plan.json`; assets via `staticFile`; `<Audio>` from `@remotion/media`; every
`interpolate` clamps both sides and guards zero-length ranges; fonts load through `@remotion/fonts`
`loadFont` before the first frame; scenes are `<Sequence layout="none">` children positioned by the plan.

## 9 · QA checklist (look at every still with your own eyes)

- **Text** — every ḥadīth word matches the card (tashkeel included); no mid-phrase wrap, no clipped glyph at the
  940 px column edge, no orphan word; tashkeel sits on the letters; the highlighted hook word is the intended one;
  honorifics complete; Arabic-Indic digits; no Latin/emoji/dialect; continuation pages say «تتمّةُ الحديث».
- **Layout & brand** — nothing important in the top 250 px / bottom 300 px; logo or `@handle` fallback present;
  points: numeral ring, chips = points count, last card lights all chips; sanad: names readable, Imam node is the
  star, seal ≤ 2 lines, note not overlapping the seal; CTA: sources ≤ 2 lines, send/save icons, fade to paper.
- **Timing & sound (`qa.json`)** — 30 ≤ duration ≤ 60 (target 42–48); `pace` 0.6–1.12; each ḥadīth line ≥ 1.3 s,
  each point card 3.6–7.5 s, seal hold ≥ 3 s; −15.5 ± 2 LUFS, true peak ≤ −1.5 dBTP; SFX land on the reveals.
- **Files** — `<slug>.mp4` (H.264 yuv420p AAC 1080×1920), `cover.jpg`, `post.md`, `contact-sheet.jpg`, `qa.json`.

## 10 · Fixing rules

Edit `content.json` (split a line, shorten a desc, drop a point) → `plan.py` → re-render. Change frame numbers
in `plan.json` only for a user-requested beat. Touch the template only for a genuine bug, then re-run both
examples in `assets/examples/`.
