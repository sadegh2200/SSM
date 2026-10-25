---
name: talking-head-studio
description: Turn a raw recording of a person talking into a finished, verified video — one command or step by step. Use when the user hands over a talking-head clip, interview, podcast, vlog, lecture, webinar or screen-and-face recording and asks to edit it, cut the dead air, remove the ums, reframe to vertical, add subtitles in Persian/Arabic/English, fix the lighting or colour, add zoom or punch-ins, stabilise it, make it louder, or deliver a Reels/TikTok/Shorts/YouTube file. Triggers include «این ویدیو را ادیت کن», «زیرنویس بگذار», «سکوت‌ها را حذف کن», «نور را درست کن», «۹:۱۶ کن», «زوم بگذار», edit my talking head, clean up this recording, cut this interview. Runs entirely locally with ffmpeg + Python (no cloud, no API key, no model download) and refuses to claim a correction it did not measure.
license: Proprietary — made for the maalsadiqeen project; third-party assets per assets/CREDITS.md.
metadata:
  title: Talking-Head Studio — استودیوی تدوین ویدیوی گفتاری
  version: 1.0.0
  output: MP4 (platform-correct) + retimed SRT + captions.ass + contact sheet + report.md + verify.json
  requires: python3 ≥3.9, ffmpeg ≥5 (ffprobe for verification), numpy, opencv-python<5, pillow
---

# Talking-Head Studio

One sentence: **give it a recording of someone talking, get back a finished video plus the proof
that it is finished** — and every change it made is a number you can disagree with.

```
python3 scripts/studio.py TALK.mp4 --out final.mp4 --captions talk.srt --preset social
```

That single line runs five stages and writes six files. Read the rest of this file only when the
user wants something the presets do not cover, or when something failed.

---

## 0. First run in a fresh environment

```bash
bash scripts/bootstrap.sh --check     # what is missing (never installs)
bash scripts/bootstrap.sh             # install what is missing, then re-check
```

It reports python, ffmpeg, ffprobe, numpy, opencv, pillow, fonts, the face cascade, and every
ffmpeg filter the pipeline uses. `studio.py` refuses to render with a clear message if the
environment is not ready; `--install` lets it run the bootstrap itself.

> A recycled sandbox loses installed packages while keeping the repo. Always run `--check` at
> the start of a session instead of trusting the previous one.

---

## 1. The five stages

| Stage | Script | What it produces |
|---|---|---|
| 1 measure | `analyze.py` | `<out>.analysis.json` — silence map, loudness, noise floor, per-sample face box, luma, motion |
| 2 decide | `plan.py` | `<out>.plan.json` — keep ranges, reframe/zoom curves, look, audio chain, caption mode, `decisions[]`, `warnings[]` |
| 3 render | `render.py` | `<out>.mp4` — one ffmpeg graph: trim → concat → reframe → look → subtitles → AAC |
| 4 verify | `verify.py` | `<out>.verify.json` + `<out>.sheet.png` — 10–12 measured checks, PASS/WARN/FAIL |
| 5 hand off | `studio.py` | `<out>.report.md`, `<out>.manifest.json`, `<out>.srt` (retimed) |

Run them by hand when you need to intervene between stages:

```bash
python3 scripts/analyze.py raw.mp4 --out a.json          # look at the numbers first
python3 scripts/plan.py a.json --out p.json --pace natural --zoom in --grade cinematic
python3 scripts/render.py p.json --out final.mp4 --preview
python3 scripts/verify.py final.mp4 --plan p.json
```

`--plan-only` on `studio.py` does stages 1–2 and stops, which is the right answer to
«first tell me what you would change».

---

## 2. Presets, and what each one actually sets

| Preset | Platform | Pace | Zoom | Grade | Captions | Use |
|---|---|---|---|---|---|---|
| `social` | reels | tight | punch | crisp | bold | Reels / TikTok / Shorts |
| `clean` | reels | natural | in | clean | bold | a calm, faithful cut |
| `cinematic` | reels | loose | in | cinematic | minimal | mood, vignette, wide dynamics |
| `podcast` | podcast | natural | none | clean | bold | landscape, no reframe |
| `raw` | original | loose | none | clean | minimal | only subtitles + loudness, no cut |

Anything a preset sets can be overridden on the same command line:
`--platform youtube --pace natural --zoom none --crop center --loudness -16`.

---

## 3. What it decides, and why — the part to read before trusting it

### Cutting
* Speech is found with `silencedetect` at −32 dB / 0.30 s. Every speech range is widened by 60 ms
  so a soft word onset is never clipped.
* **Nothing is ever cut inside a speech range.** Only dead air: the head, the tail, and interior
  pauses longer than the pace threshold (`tight` 0.30 s → keeps 0.16 s, `natural` 0.60 → 0.30,
  `loose` 1.10 → 0.55).
* `--max-duration` never deletes words to fit. If the cut is longer than the target, you get a
  warning that says so and the full cut is rendered.

### Reframing
* A face box is measured per sample (Haar cascade shipped in `assets/cascades/`), the largest box
  wins (the speaker, not a face on a bookshelf), and each **take** gets the *median* centre — so
  the frame does not chase every head movement.
* Focus points are mapped through the cover-crop maths (`filters.cover_map`), which is the step
  most reframe tools get wrong: a face at 52% of the source is not at 52% of a 9:16 crop.
* `--fit auto` measures the magnification. If a cover crop would magnify more than ~1.55× **and**
  the projected face would exceed half the frame width, it switches to a blurred-fill band
  (the whole subject, hero band cropped to 4:5, blurred copy behind). Override with
  `--fit cover|pad`, `--band 0.5–0.9`, `--anchor`.
* No face → centre crop **plus an explicit warning**. Never a silent guess.

### Zoom
Per-take curves over output time: `punch` (push-in that holds), `pulse` (in/out pairs), `in`
(one slow push for the whole piece), `out` (reveal), `none`. Amplitude defaults to 6% — the range
where a push reads as "energy" rather than "wobble". Never more than one move per take.

### Light and colour
* Exposure target is **the subject's own luma** (median over the face box), 132/255, not the frame
  average — a dark wall behind a well-lit face must not darken the face.
* A temporal correction curve is applied when the exposure swings more than 18 luma units across
  the clip (window light, auto-exposure hunting).
* White balance is grey-world with a hard ±0.09 clamp — enough to kill a green fluorescent cast,
  never enough to invent a look.
* Grades are deliberately small: `clean` (+2% contrast, slight unsharp), `warm`, `crisp`,
  `cinematic` (contrast, −4% saturation, vignette). Anything bigger is a design decision, not a fix.

### Audio
* Noise floor is the 5th percentile of per-window RMS. `> −30 dB` → aggressive `afftdn`,
  `−30…−45` → gentle, `< −45` → **no denoise at all** (denoising clean audio only damages it).
* High-pass at 75 Hz, mud cut at 250 Hz, presence at 3.2 kHz, always.
* Loudness is measured on the **trimmed** audio (a second decode pass) so the target is reached on
  the real cut, not the raw file; `loudnorm` then runs linear with those measurements.
  Defaults: −14 LUFS / −1.5 dBTP (social), −16 (podcast), −23 (broadcast).

### Captions
SRT/VTT in, ASS out, **cue times pushed through the cut map** — this is the step almost every
pipeline gets wrong: the moment you remove 4 s of dead air, every cue in the user's SRT points at
the wrong second. Cues that straddle a cut are split; empty parts are dropped; a retimed
`<out>.srt` is written beside the MP4 for platforms that take their own captions.

Reading speed is checked (17 chars/s Latin, 14 for Arabic/Persian) and reported per cue — it is
never silently rewritten, because the words are the author's.

> **`Spacing` must stay 0 in the ASS style.** A non-zero letter-spacing makes this libass draw
> Arabic/Persian glyphs unjoined and in logical order — mirrored garbage. This was found by
> bisection; do not "improve" tracking in `captions.py`.

For Persian/Arabic the style flips to `Vazirmatn` (shipped) at bottom-centre, and the bottom
margin is computed from the platform's UI-safe area (16% of height for Reels).

**No transcription is invented.** If the user has no SRT, say so and offer: (a) they paste/attach
a transcript, (b) a word-level JSON for karaoke, (c) deliver uncaptioned and add text later.
Never fabricate dialogue.

---

## 4. Talking to the user

Report in this shape — it is also what `<out>.report.md` contains:

```
✓ final.mp4  0:47 (from 1:12, −25s dead air, 9 cuts)
  verdict: PASS — 11 checks, 11 pass
  · 7 pauses shortened, head and tail trimmed
  · reframe: speaker centred per take (face in 96% of samples)
  · exposure: subject luma 98 → +13% brightness
  · loudness: −19.4 → −14.0 LUFS
  · captions: 24 cues remapped through 9 cuts
```

Rules:
1. **Never say "done" without the verdict line.** If `verify.json` says FAIL, the video is not delivered.
2. **Say what was declined.** "No noise reduction: the floor was already −52 dB" is a feature.
3. **Warnings are part of the answer**, not a footnote — clipping, no face, soft source, silent
   track, and "your target length does not fit without cutting words" all change what the user should do.
4. Persian or English, matching the user. Numbers with the units that were measured (LUFS, luma, s).

---

## 5. Failure ladder

| Symptom | Cause | Fix |
|---|---|---|
| `environment not ready: filter:ass` | static ffmpeg without libass | `bash scripts/bootstrap.sh`, or use a distro ffmpeg with libass |
| `encode failed` + `matches no streams` | source has no audio | re-run studio.py (fixed in 1.0); if it persists, check the probe in `plan.json` |
| captions appear mirrored/unjoined | ASS `Spacing` ≠ 0, or a font without Arabic | keep `Spacing: 0`; use `--caption-font assets/fonts/Vazirmatn.ttf` |
| face not found | profile view, heavy shadow, mask | `--crop center` and accept a centred cut; tell the user why |
| output too tight / face too large | cover crop on a wide source | `--fit pad --band 0.62` |
| renders slowly | 1080p cover crop + zoompan on 1 core | `--preview` to iterate, final render once |
| loudness off by >1.5 LU | source has long silence inside the cut | check `warnings[]`; re-run with `--pace natural` |

Long-form: full details in `references/`.

---

## 6. What this skill will not do

* **No transcription.** Speech-to-text models are not downloaded here; captions need an SRT.
  (Companion skills that do have ASR: `cut-video`, `clipify`, `talking-head-editor`, `video-use`.)
* **No generative video, no avatars, no music.** It edits what exists.
* **No word-level cutting.** It trims pauses; it does not remove ums mid-sentence — the
  measurement that would need (word timings) requires ASR.
* **No claim of measurement when a measurement failed.** Missing numbers stay `None` and appear as
  a warning. That is deliberate: a silent "looks fine" is the most expensive bug in an editor.
