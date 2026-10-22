# QC gates (nothing ships without all of them)

> **v3 adds three machine gates before the four below:** `copy_lint.py` (on-screen wording),
> `captions.py` (IG/FB/X limits) and `comments.py` (seven slots). `social_kit.py` aggregates them into
> `validation.md`; `verify.py --kit <dir>` reads that verdict, and `verify.py --source-spec` runs the
> copy gate inside QC. A red `validation.md` blocks delivery.

## Gate 1 — Content (before any code)

- [ ] One idea in ≤ 14 words; archetype chosen; brief filled (content-analysis.md §5).
- [ ] Every quoted text matches the sheet letter for letter (tashkeel included); unreadable spots flagged.
- [ ] References complete (book ج/ص) or the proof block dropped; grading words not invented.
- [ ] Honorifics correct; no polemics; no exclamation marks/emojis; ≤ 70 on-screen words total.
- [ ] Audio plan: recitation ref + edition, or "no verse → sound design only"; no narrator unless asked.

## Gate 2 — Spec & build (`build_reel.py`, `mix.py`)

- [ ] `build_reel.py` prints no `WARN` (or each warning is consciously accepted).
- [ ] Verse scene ≥ recitation + 1.6 s; `cues.words` count = number of words.
- [ ] `mix.py` prints a final LUFS within ±0.5 of target and the event list looks like the design table.

## Gate 3 — `verify.py <project>` (pre-render)

- [ ] 0 failures; warnings read and resolved or accepted.
- [ ] `hyperframes check` passed with the browser session (contrast 100 %, layout 0 issues).
- [ ] `qc/sheet.jpg` inspected frame by frame: typography sizes sane, no clipping, emphasis gold present,
      seal visible, watermark clear of text, brand card centred with handle.
- [ ] Hook frame at 1.2 s works as a thumbnail (would you stop scrolling?).

## Gate 4 — `verify.py <project> --render out.mp4` (post-render)

- [ ] 1080×1920, 30 fps, duration = spec ± 0.15 s, AAC audio present.
- [ ] Integrated LUFS within ±1.2 of target; true peak ≤ −0.8 dBTP.
- [ ] Scrub the MP4 at the same key times (ffmpeg frame grabs) — the render must match the snapshots;
      a blank render means `dir=rtl` on `<html>` or a font that failed to load.
- [ ] Watch once at 1× with sound, once muted. Muted must still make complete sense.

## Common defects and their fixes

| symptom | cause | fix |
|---|---|---|
| blank/paper-only video | `<html dir="rtl">` | remove; `direction: rtl` on elements only |
| text cut at the right edge | manual size override too big / line too long | remove `size`, cut words |
| word lands before the recitation says it | cue too early | shift `cues.words[i]` +0.1–0.2 s |
| bed pumping | one-pass loudnorm | mix.py already uses static gain + limiter; don't post-process |
| ffmpeg mix hangs forever | infinite `apad` on the sidechain | mix.py pads to `whole_dur`; keep it |
| render aborts "Low disk space /tmp" | TMPDIR | `source scripts/env.sh` (sets TMPDIR to ~/.cache/tmp) |
| `Code: 127` launching browser | missing shared libs | `ldd chrome-headless-shell \| grep "not found"` → apt-get |
| Persian text wraps | Persian ≈ 20 % longer | smaller sizes / `nowrap` / fewer words |
