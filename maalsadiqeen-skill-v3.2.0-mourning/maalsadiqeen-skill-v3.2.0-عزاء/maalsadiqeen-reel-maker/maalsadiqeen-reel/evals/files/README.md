# Eval input files

## Committed fixtures (self-contained evals)

| file | used by | what it tests |
|---|---|---|
| `chapter-short.md` | eval 2 | a short text with a verse, a graded ḥadīth and a scholar's line → archetype A, three layers, seal only because the grading is stated |
| `lecture-long.md` | eval 3 | three independent ideas in 294 words → the agent must propose a series, not cram |
| `hadith-no-source.md` | eval 4 | a ḥadīth with the reference cut off → no invented source, no seal |
| `objection.md` | eval 5 | an objection with a calm answer → archetype F, no sect named |
| `spec-9-119.json` | evals 6, 7, 8 | a clean 45 s spec (6 scenes) → captions/comments only, A/B variant, missing-toolchain degradation |
| `essay-one-idea.md` | evals 9, 10 | 525 words, four sections, **one** idea (الوفاء بالعهد) → a G–L reel with a `paragraph`/`definition`, not a series and not a summary |
| `chapter-short.md` | eval 13 | the same A-type text, now for the ending doctrine: the agent must refuse «أرسلها لمن تحب» |
| `objection.md` | eval 14 | a heavy text in the mourning palette — no invitation at all |
| `copy-errors.md` | eval 12 | a card with deliberate hamza / ta-marbuta / digit / dialect / «!» errors around a correctly vocalised verse → `ar_copycheck.py` must catch them without touching the verse |

All fixtures are original text written for this repository; they are not copied from any published
book. The references inside them (الكافي ج١ ص٢٠٨، مرآة العقول ج٢ ص٤٢١) are the same ones used in
`assets/examples/` as a worked example — treat them as sample data, and verify before publishing.

## Private fixtures (not committed)

Eval 1 references the page's three original carousel cards (`sheet-1.jpg`, `sheet-2.jpg`,
`sheet-3.jpg` — the «كونوا مع الصادقين» post). They are the page owner's property: copy them into this
folder before running that eval.

Rendered references for visual comparison: `assets/examples/sadiqeen-9-119.sheet.jpg` and
`assets/examples/hadith-only.sheet.jpg`.
