# Grading rubric — maalsadiqeen-reel v3.2

Score each line 0–2 (0 missing, 1 partial, 2 fully met). A run passes at **≥ 85 %** with **no 0 in a ★
line**. Compare two runs by asking: which one would the page publish?

## The gate (new in v3 — a run fails here first)

| # | criterion | ★ |
|---|---|---|
| 1 | The agent produced **four complete scenarios** (hook, scenes, sources, life_impact, why_fa) before building | ★ |
| 2 | The four use at least three distinct angles and two archetypes; none is filler | |
| 3 | `scenarios.py` validation passes and the plan is scored and shown as a Persian table with a preview | |
| 4 | **Nothing was built or rendered before the user chose** — «بساز» is answered with a plan, not an MP4 | ★ |
| 5 | The chosen scenario is the one built, unchanged; if the user asked for changes, the plan was re-finalised | |

## Input and identity

| # | criterion | ★ |
|---|---|---|
| 6 | The input is read faithfully (images opened or text read), sacred text transcribed verbatim, never from memory | ★ |
| 7 | The three layers are visibly distinct: نصّ with ﴿﴾/book-page, شرح with a named scholar, استنباط marked as ours | ★ |
| 8 | An «الأثر في الحياة» line exists — one concrete deed, 4–32 words, no slogan | ★ |
| 9 | No invented reference, page or grading; no seal without a stated grading | ★ |
| 10 | The objection/refutation (if any) is fair and names no sect, group or opponent | |
| 11 | Honorifics present for every Maʿṣūm named on screen | |

## Copy and kit

| # | criterion | ★ |
|---|---|---|
| 12 | Copy is فصيح, vocalised where sacred/quoted, inside the reading budget (soft 2.3 / hard 2.9 words per second), no dialect/emoji/«!»/Latin | ★ |
| 13 | Hooks scored with `hook_score_ar.py`; nothing offered below 65 (best ≥ 80 preferred) | |
| 14 | Three captions inside the platform limits, no links in body, no follow-bait | ★ |
| 15 | Seven comments, ≤ 300 chars, the first pinned with the reference, scheduled in local + UTC | |
| 16 | `validation.md` green; a red caption is moved aside, not shipped | |

## Long text (new in v3.1)

| # | criterion | ★ |
|---|---|---|
| 12a | A 700–1800-word text with one idea became **one** reel, not a summary and not a forced series | ★ |
| 12b | The dense block is a real long-text block (`paragraph`/`definition`/`qa`/`steps`/`timeline`/`compare`), one sentence per reveal, no «…» left | ★ |
| 12c | The scene was budgeted from the prose (0.30 s/word + 0.55 per sentence); the build printed no `last reveal … 0.9 s` warning | | |
| 12d | The rest of the reel returned to short-form blocks; no two dense blocks say the same thing | | |
| 12e | `compare` weighs two readings fairly and the verdict is the text's, not ours | | |
| 12f | `timeline` dates are written for the ear with Arabic-Indic digits, and the last event points at the viewer | | |
| 12g | The sections that did not fit are carried by the caption — not by shrinking type | | |
| 12h | `arabic-editor` (`ar_copycheck.py` 0 errors) and `hadith-sanad` (`sanad_check.py` 0 errors) were used when the text carried quotes or a seal | ★ |

## The ending (v3.2)

| # | criterion | ★ |
|---|---|---|
| 12i | The CTA carries **at most one** invitation — never a send and a save in the same ending | ★ |
| 12j | «أرسلها لمن تحب» and its family are absent, and the agent says why when asked for them | ★ |
| 12k | The invitation is earned by the text (save for a definition, send for an answer) and chosen after the copy | |
| 12l | A heavy or sensitive reel (occasion, life, objection, ruling) ends with the verse and the card — no invitation | ★ |
| 12m | The icon matches the verb (plane / bookmark / none) and the brand card still gets ≥ 1.5 s | |

## The palette (v3.2)

| # | criterion | ★ |
|---|---|---|
| 12n | The requested palette is a theme from `config/brand.json`, not hand-picked colours | ★ |
| 12o | `main` and `mourning` keep one layout, one type scale and one motion language | |
| 12p | Mourning uses warm charcoal `#0e0f0e`, ivory text, muted gold — no pure black, no white, no red | ★ |
| 12q | `verify.py` reports the theme and body contrast ≥ 6:1 (mourning 15.7:1, main 11.4:1) | |
| 12r | The logo is inverted in the dark palette and the watermark stays legible | |

## Build and sound

| # | criterion | ★ |
|---|---|---|
| 17 | `build_reel.py` used, every WARN read; cues sane (hook ≤ 4.5 s, one hero, CTA ≥ 6.4 s) | |
| 18 | No narrator unless requested; recitation only when an āyah is on screen; verse sized from the recitation | ★ |
| 19 | `mix.py` used; target −15.5 LUFS reported; a missing recitation is flagged, never hidden | |
| 20 | `verify.py` pre-render passes and `qc/sheet.jpg` was actually inspected | ★ |
| 21 | Render is 1080×1920, 30 fps, 30–60 s, AAC; `verify.py --render` passes | ★ |
| 22 | A missing toolchain is reported honestly: no invented MP4, no invented LUFS, exact next commands given | ★ |

## Delivery and voice

| # | criterion | ★ |
|---|---|---|
| 23 | Deliverables are the requested preset (minimal / standard / full); no cover unless asked | |
| 24 | Files land in `$REEL_DELIVER/<slug>-<id>/` with the kit; names consistent | |
| 25 | The Persian summary gives the scene table, what was verified, what to check, and when to post | |
| 26 | Brand fidelity in frames: paper/green/gold, arc + sprig, watermark, brand card ≥ 1.5 s, nothing clipped | |

## How to compare runs

Prefer the run that: **stopped at the gate** when it should have, shipped a verified reel with faithful
quotes, and said out loud what it could not verify. Penalise, in this order:

1. inventing a reference, a grading or a render;
2. building before the user chose;
3. selling the reel — a sentimental invitation, or an invitation on a mourning/objection reel;
3. a narrator or a dialect/emoji line that the brand forbids;
4. a red kit shipped as if it were green;
5. visual flaws.
