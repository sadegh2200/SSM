---
name: sadiqeen-studio
description: Use when the user wants a reel, a short vertical video, a poster-grade clip, or a «ریل» / «ویدیو» for «مع الصادقين» (@maalsadiqeen) — or hands over any Arabic religious text (a page, a transcript, a forwarded message, a question, an objection, an occasion) and wants it turned into one calm, sourced, 30–60 s 1080×1920 video. Also use when the user asks to redesign, re-time, re-style, re-voice or QA an existing «مع الصادقين» reel, to diagnose why a reel looks amateur, or to produce the publishing kit (three captions, the comment bank, the schedule) for one. Also use when the user hands over **a recorded take** — a phone or laptop video of a scholar — and asks to «ادیت» it, «حرفه‌ای‌اش کن», make a reel out of it, or dress it in the brand: `footage.py` measures the take, cuts at the pauses, covers every cut with a card, and grades it (see `references/05-footage.md`). Triggers on «ریل بساز», «از این متن ریل دربیار», «این ویدیو را حرفه‌ای کن», «روی این ویدیو کار کن», «همین سبک مع الصادقین», "make it look like the page", "edit my recording", and on any request to render a reel spec to MP4 without node, HyperFrames or a browser.
license: Proprietary — made for the maalsadiqeen page. Fonts and sound cues come from the installed `maalsadiqeen-reel` skill (OFL fonts, licensed SFX — see its assets/sfx/CREDITS.md).
metadata:
  title: Sadiqeen Studio — استودیوی مع الصادقین
  version: 2.0.0
  brand: maalsadiqeen
  output: 1080×1920 MP4 (30 fps, ≤60 s, h264+aac, −15.5 LUFS) + contact sheet + report + kit
  requires: python3 ≥3.9 (numpy, pillow, uharfbuzz, freetype-py), ffmpeg; the maalsadiqeen-reel skill installed beside this one (brand tokens, fonts, logo, sound cues, copy gates)
  engine: PIL + HarfBuzz + ffmpeg — no node, no browser, no network
---

# Sadiqeen Studio (`sadiqeen-studio`)

You are not making a video. You are making **a page that moves**: cream paper (or charcoal at
night), one idea, one hero line, gold hairlines, sacred text set properly in Amiri Quran, and a
proof card that says exactly where the sentence came from. If a frame could be screenshotted and
pasted into the brand's printed sheets without anyone noticing, the frame is right.

The studio exists because two things are hard and everything else is easy:

1. **Arabic type that is actually correct.** Pillow in most sandboxes has no libraqm, so the
   default renderer draws unjoined, reversed letters. This skill shapes with HarfBuzz and
   rasterises with FreeType, and it knows the four traps that follow (see
   `references/02-type-and-stage.md`).
2. **A sentence the brand is allowed to say.** Who wrote it, which Imam, which book, which page,
   which grade — the installed checkers own that, and this studio runs them **before** the first
   frame.

Everything else — the clock, the motion, the mix, the gate, the kit — is deliberate, numeric and
repeatable.

## The five stages

| # | stage | who does it | artefact | gate |
|---|---|---|---|---|
| 1 | **Recognize** | `director.py recognize` then you | `recognition.json`, `brief.md` | confidence · the three questions · what is missing |
| 2 | **Treat** | `director.py treat` | `treatments.json` | ⛔ three scored angles — **the user picks** |
| 3 | **Write** | you | `spec.json` | `brandgate.py` = copy_lint · ar_copycheck · sanad_check · hook_score |
| 4 | **Build** | `studio.py build` | MP4 + `mix.wav` + kit + sheet | renders only after stage 3 is green |
| 5 | **Verify** | `studio.py verify` | `report.md`, `report.json`, `contact-sheet.png` | 0 fails, ≤2 warns |

Stage 2 is a stop, not a formality. Nothing is rendered until the user has chosen an angle.

## Non-negotiables

1. **Gates before pixels.** `brandgate.py` runs the brand's own checkers. A red gate is not
   rendered. `--force` exists for experiments and is never used for a delivery.
2. **No invented reference, no invented grading.** No source → no proof block, and the Persian
   summary says so. A seal without a stated grade is a `copy_lint` failure.
3. **One idea, ≤ 14 words to state it.** If it does not fit, it is two reels or a series.
4. **One hero per reel**, at 50–65 % of the runtime. The closing line (`cta.final`) is not a hero.
5. **9:16 1080×1920, 30 fps, ≤ 60 s**, default 40 s. Text never crosses x 150–950, y 300–1440.
6. **Light palette unless the occasion is a mourning one.** `main` (النهار) is the default;
   `mourning` (ليلُ العزاء) is for Muharram, Ṣafar, Ramadan nights and death anniversaries.
7. **No red, no pure black, no pure white, no glow, no drop shadow** — in either palette.
8. **One invitation at most, and usually none.** «أَرْسِلْهَا لِمَنْ تُحِبّ» is forbidden.
9. **Every number in the report comes from a measurement**, never from memory.
10. **Reply in Persian; on-screen copy in Classical Arabic.** The reel must make sense muted.

## Footage mode — the recording is the picture

Some briefs are not text-first. The user has already spoken on camera, and the job is to make the
take behave like the page. Same brand, same type, different substrate:

```bash
python3 footage.py probe  raw.mp4                   # rotation · fps · duration · audio
python3 footage.py pauses raw.mp4                   # the only honest cut points
python3 footage.py build  edit.json --out deliver/  # cut · grade · type · sound · verify
```

The doctrine, in four lines:

1. **No word is removed and no jump cut is seen.** Pauses are shortened, never deleted (`lead`
   0.12 s stays at each end) and every shortened pause sits inside a full-frame card — the cut is
   hidden by paper, the splice is inside silence. `audit()` fails the build if a cut is uncovered.
2. **The grade removes the phone.** Filmic S-curve, warm highlights, blacks lifted not crushed,
   vignette, grain, and a 5% push-in. Nothing is applied that the frame does not need.
3. **Type lives on a falloff, not in a box.** Chyrons bottom-right over a dithered scrim, snapped to
   the syllable he actually breathes before; cards own the frame when he pauses.
4. **No music.** Denoise, presence, gentle compression, two-pass −15.5 LUFS. A bed under a hadith is
   the fastest way to make it cheap.

`verify()` then measures the finished file, including **contrast per chyron sampled from the real
frame** — that is the check that catches a pale hand passing behind the words.

## Run it

```bash
export PATH=/home/user/bin:$PATH            # ffmpeg shim, if the sandbox has none
cd <skill>/scripts
python3 studio.py doctor                    # deps · fonts · brand · theme · sound cues
```

**Stage 1 — recognize** (any input: `.md`, `.txt`, `.srt`, a folder, a spec, a video with a
sidecar `.srt`):

```bash
python3 studio.py recognize input.md --out work/
cat work/brief.md            # class A–F · the one idea · verses · references · grades · what is missing
```

**Stage 2 — treat** (three angles, scored, never four variants of the same idea):

```bash
python3 studio.py treat work/recognition.json --out work/
# → table: angle · hook · block shape · duration · score ; and the pick
```

Write `work/spec.json` from the chosen treatment (the field reference is
`references/01-pipeline.md`). Then:

**Stage 3 — the copy gate:**

```bash
python3 brandgate.py work/spec.json         # copy_lint · ar_copycheck · sanad_check · hook_score
python3 -m json.tool work/spec.json >/dev/null   # and: is it contiguous? is it valid JSON?
```

**Stage 4 — build** (the gate runs again inside `build`; this is the only door to a render):

```bash
python3 studio.py build work/spec.json --out deliver/ [--theme mourning] [--no-audio]
#   0. copy gate         (≤2 s)
#   1. frames → silent   (~6.5 fps: 40 s ≈ 3 min)
#   2. cues → mix        (bed + SFX, loudnorm −15.5 LUFS)
#   3. mux + verify      (report.md, contact-sheet.png, kit/)
```

**Stage 5 — verify and deliver:**

```bash
python3 studio.py verify deliver/reel.mp4 --spec work/spec.json --sheet deliver/contact-sheet.png
python3 studio.py still work/spec.json 12.4 --out check.png   # any single frame, for a look
```

Deliver: the MP4, the contact sheet, `report.md`, `copy-gate.md`, and `kit/` (three captions, seven
comments, `publish.md`, `.srt`, alt text). Present the MP4; state the verdict and every warning.

## The studio's own two numbers

- **Frame cost ≈ 155 ms** (paper + grain plates + ~8 elements). A 40 s reel is ~3 minutes of
  compute. This is why the copy gate is in front: a re-render for a comma is 3 minutes.
- **Word budget:** soft `max(95, 2.3·duration)`, hard `max(110, 2.9·duration)`. At 40 s that is
  95 / 116 words. Prose blocks are what makes 120 words watchable; two prose blocks that explain
  the same thing are one too many.

## The fifteen blocks

| family | block | what it is | typical s |
|---|---|---|---|
| short | `hook` | lead · line1 · line2 · sub + gold underline | 3.0–4.5 |
| short | `verse` | āyah word by word, highlight in gold, drawn «﴿ ﴾» | 8–14 |
| short | `quote` | a ḥadīth or a scholar's sentence + attribution | 8–12 |
| short | `contrast` | what it is **not** vs what it is, gold strike | 6–9 |
| short | `answer` | one hero line — the screenshot frame | 7–9 |
| short | `proof` | seal + `book · vol/page · grade` cards | 7–10 |
| short | `list` | ≤ 4 items, Arabic-Indic numerals | 8–10 |
| short | `title` | occasion / section card | 3–4.5 |
| short | `cta` | take-away + ≤1 invitation + brand card | 6.4–7.4 |
| long | `paragraph` | a passage, one sentence at a time, right-aligned | 10–16 |
| long | `definition` | term, then its حدّ, then one note | 9–13 |
| long | `steps` | 2–4 ordered steps | 11–15 |
| long | `timeline` | 2–4 moments on a gold spine | 12–16 |
| long | `compare` | two readings side by side, then the verdict | 11–15 |
| long | `qa` | a real question answered in sentences | 12–18 |

Cues come from reading speed: `max(1.15, 0.26·words)` for a short line,
`max(1.80, 0.30·words + 0.55)` for a prose sentence, `+0.18 s` of air between reveals. A reveal
less than 0.9 s before the cut is a warning, and the fix is to extend the scene — never to cut the
sentence in half.

## Decision table

| situation | do |
|---|---|
| a verse **and** a ḥadīth | class A · verse block with recitation · `answer` hero · `proof` |
| a ḥadīth with a reference, no verse | class B · `quote` with `hero: true` · proof without a seal unless a grade is stated |
| a concept, a scholar's analysis | class C · `contrast` carries the turn · `proof` |
| a question people ask | class D · `qa` · answer ≥ 8 s |
| a date, a person, an occasion | class E · `title` first · `mourning` palette · no invitation |
| an objection | class F · state it fairly, answer from the text, never name a group |
| 700–1800 words, one idea | **one** dense block (`paragraph`/`definition`/`qa`) + four short ones |
| > 1800 words | a series, one reel per idea — say so before writing |
| the user asks for a cover/poster | `still` at the hero second; do not add a block |
| the user asks for > 60 s | decline; propose two parts with the same opening |
| the gate fails on a sacred line | stop, fix the wording or the grade with `arabic-editor` / `hadith-sanad` |
| no font/brand skill installed | `doctor` says so; the tokens fall back to the snapshot, fonts do not |
| no ffmpeg | frames still render; `--no-audio` writes the silent master and the report says so |

## Failure ladder — degrade honestly

1. **Brand skill missing** → tokens come from the snapshot in `brandkit.py`; fonts, logo and SFX do
   not. `doctor` refuses, and you say which of the three is missing.
2. **Checkers missing** → `brandgate` reports `warn`, never `pass`, and the summary says the copy
   was not gated.
3. **No ffmpeg** → `--no-audio` silent master, and `verify` skips loudness instead of guessing.
4. **A block cannot fit its copy at the minimum size** → the builder keeps the minimum and the
   warning is your cue to cut words, not to shrink the type.
5. **Never** call a placeholder a master, and never present a WARN reels as clean.

## What this studio will not do

- it will not invent a reference, a grade, a date or a quote;
- it will not put an unverified sacred line on screen;
- it will not use a synthetic narrator (recitation is welcome; a voice-over needs the user's
  explicit ask, and then `references/03-sound.md` §narration);
- it will not mix engines (no browser, no node, no HyperFrames project in the middle);
- it will not publish, schedule or touch an account;
- it will not “improve” the brand's tokens, its copy lint, or its CTA doctrine.

## Files

| path | what |
|---|---|
| `scripts/studio.py` | front door: `doctor` · `recognize` · `treat` · `build` · `verify` · `kit` · `still` |
| `scripts/director.py` | recognition + three treatments (+ `brief.md`) |
| `scripts/brandgate.py` | runs the four brand checkers as gates; `copy-gate.md` |
| `scripts/plan.py` | spec → clock: cues, reading speed, word budget, audit |
| `scripts/blocks.py` | the fifteen block recipes; writes the sound cues as it draws |
| `scripts/typo.py` | HarfBuzz + FreeType typesetting: shape, measure, wrap, fit, paragraph |
| `scripts/stage.py` | paper, grain, light sweep, arc, sprig, logo, motion, seal, flourish |
| `scripts/render.py` | frames → MP4 (PIL → rawvideo → ffmpeg), `--still` for one frame |
| `scripts/sound.py` | bed (the brand's `gen_bed.py`) + cue track + ducking + loudnorm |
| `scripts/verify.py` | the numeric gate + contact sheet + `report.md` |
| `scripts/kit.py` | captions, comment bank, schedule, alt text |
| `scripts/footage.py` | footage mode: probe · pauses · cut plan · cards & chyrons · grade · mix · verify |
| `scripts/brandkit.py` | tokens from `config/brand.json`, geometry, fonts, assets |
| `references/01-pipeline.md` | every spec field, the recognition contract, the treatment rules |
| `references/02-type-and-stage.md` | the type stack, the four traps, layout table, safe zones |
| `references/03-sound.md` | bed, cues, ducking, LUFS, recitation, narration |
| `references/04-qc.md` | the gates, the numbers, the five-minute human review |
| `references/05-footage.md` | a recorded take: measuring, cutting at pauses, the grade, the type layers, the mix |
| `evals/` | eight test prompts, the rubric, and `fixtures/sample-class-a.md` (a 90-word class-A text with two grades and one verse — the end-to-end smoke test) |

## Done means

- The user chose the treatment; `treatments.json` holds three scored angles.
- `brandgate` = 0 fails (warns are named in the summary) — copy_lint, ar_copycheck, sanad_check.
- `report.md` = 0 fails; every number measured; the contact sheet exists and was looked at.
- The MP4 is 1080×1920 · 30.000 fps · h264/yuv420p + aac · −15.5 ±1.2 LUFS · ≤ −1.0 dBTP.
- `kit/` has three captions inside their limits, seven comment slots, a schedule in the brand's
  timezone, an `.srt` and alt text.
- For a footage edit: every cut is covered by a card, `report.md` passes, and the measured chyron
  contrast is ≥6:1 on the real frame.
- The Persian summary says: the one idea, the angle the user chose, the block table, what was
  verified, what is uncertain (missing reference, unverified wording), and what to check by eye.
