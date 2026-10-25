# Rubric — grading a `sadiqeen-studio` run

Eight criteria. Each is **pass / fail** with one anchor sentence; total = 8. A delivery below 8/8
is not delivered — it is a draft, and the summary says which criterion failed.

| # | criterion | pass means | fail means |
|---|---|---|---|
| 1 | **Pipeline discipline** | the run went recognize → treat → **stop** → write → gate → build → verify, and each artefact is on disk (`recognition.json`, `treatments.json`, `spec.json`, `copy-gate.md`, `report.md`) | it jumped to a spec, or the user never chose the treatment |
| 2 | **Type is right** | every Arabic line is joined and reads right-to-left; no tofu box; harakat sit on their letters; the verse label carries drawn «﴿ ﴾» | any reversed/unjoined word, any ▯, any bracket typed from a font that lacks it |
| 3 | **Composition** | one idea per frame, one hero at 50–65 %, right-aligned prose, everything inside x 150–950 / y 300–1440, nothing under the watermark | centred paragraphs, two heroes, text in the platform UI band |
| 4 | **The brand's tokens** | palette, fonts, arc, sprig, logo, three text sizes max, no red, no pure black/white | a different palette, a system font, a glow or a shadow |
| 5 | **Words survive the gate** | copy_lint 0 fails, ar_copycheck 0 fails, sanad_check 0 fails; hook_score ≥ 65 and reported | any gate fail; a hook scored and ignored |
| 6 | **Numbers measured** | `report.md` shows frame, fps, duration, codecs, LUFS, true peak, contrast, word budget — each from a measurement; ±1.2 LUFS | a number copied from the spec, or “looks fine” |
| 7 | **The honest summary** | Persian: the one idea, the chosen angle, the block table, what was verified, **what is uncertain**, what to check by eye | a summary that claims everything is perfect, or hides a missing reference |
| 8 | **The kit** | three captions inside their limits, seven comment slots, schedule in the brand's timezone, `.srt`, alt text | captions over a limit, no comment bank, no schedule |

## Fail-fast list (any one of these ends the review)

- an invented reference, grade, date or quote;
- a sacred line on screen without tashkeel, or with a wording nobody verified;
- a seal drawn without a stated grading;
- a reel rendered after a red copy gate (`--force` used for a delivery);
- the brand's CTA doctrine broken (two invitations, «أَرْسِلْهَا لِمَنْ تُحِبّ», or an invitation on
  an occasion);
- a delivery with no `report.md`, or a `report.md` with an unmeasured number in it.

## Grading notes

- Criterion 2 is looked at **at 100 %** (a crop of one line), not on the contact sheet.
- Criterion 3 and 4 are looked at on the contact sheet **and** at 30 % size (the phone test).
- Criterion 6 is checked by re-running `verify` on the delivered file, not by reading the report.
- Criterion 7 is the one graders forget: a run that is technically clean but silent about a missing
  reference is a fail.
