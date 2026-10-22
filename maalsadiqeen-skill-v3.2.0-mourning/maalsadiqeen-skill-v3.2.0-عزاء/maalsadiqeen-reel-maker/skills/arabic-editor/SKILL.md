---
name: arabic-editor
description: Use when classical Arabic copy has to be written, vocalised, proofread or cut to length — a reel line, a hook, a caption, a comment, a title, a quote — for «مع الصادقين» (@maalsadiqeen), or whenever `copy_lint` reports a tashkeel, spelling, punctuation or register problem. Four passes — register, orthography, tashkeel, punctuation and line breaks — with `ar_copycheck.py` as the mechanical half. Triggers on «اعراب گذاری», «تشکیل», «ویرایش عربی», «این جمله درست است؟», "check the Arabic", "add tashkeel", and on any Arabic line longer than the block that must hold it.
license: Proprietary — made for the maalsadiqeen page.
metadata:
  title: Arabic editor — محرّر العربية
  version: 1.0.0
  scope: on-screen lines, captions, comments, titles, alt text
  pairs_with: maalsadiqeen-reel (copy_lint.py), hadith-sanad (for quoted text)
---

# Arabic editor — the copy pass before anything is rendered

The page's voice is **calm, classical, scholarly**. That is a typographic claim as much as a moral
one: a misplaced hamza costs more authority than a strong sentence gains. This skill edits Arabic
copy in four passes, in this order, and never skips one.

```
1 register  → is this fusha, and is it the page's fusha?
2 orthography → hamza, ta marbuta, alif maqsura, numbers
3 tashkeel  → how much, on which letters, for which layer
4 punctuation & line breaks → «، ؛ ؟ …» and where the line ends
```

> **It never edits sacred text.** A verse or a ḥadīth is transcribed exactly as transmitted. If a
> word looks wrong, the fix is `[؟]` and a question to the user — never a correction from memory.
> For the provenance of a quotation, use `hadith-sanad`.

---

## 1 · Register

| rule | example |
|---|---|
| Fusha only. Dialect words are errors, not flavour. | «كتير» → «كثير» · «شو» → «ماذا» · «هلأ» → «الآن» |
| No journalese, no management-speak, no «رائج» vocabulary. | «يُعدّ … من أهم» → «… من» |
| No clickbait openings, no second-person shaming. | «هل أنت مخطئ؟» → «يَظُنُّ كَثِيرُونَ…» |
| No exclamation marks, no question stacks. | «ماذا تعرف؟!» → «مَاذَا تَعْرِف؟» |
| Address the reader once, in the plural or the singular, never mixed. | «اعلموا» or «اعلم» — pick one per reel |
| One idea per line; a line is a thought, not a clause. | split at «،» before splitting at the screen edge |

Full table and the 20 banned constructions: `references/register.md`.

## 2 · Orthography

The errors that actually appear in this project's copy:

| wrong | right | why |
|---|---|---|
| إنشاء الله | إن شاء الله | «إنشاء» = creation |
| اللة | الله | the ta marbuta is not a ha |
| مسئلة | مسألة | hamza on wāw seat, not yāʾ |
| شئ | شيء | final hamza sits on the line, after yāʾ |
| إبتداء · إستغفار · إجتماع | ابتداء · استغفار · اجتماع | hamzat waṣl, no hamza written or pronounced |
| الأئمة | الأئمّة (or الأئمة) | both accepted; keep one per file |
| علي (for على) | على | alif maqṣūra vs yāʾ — a meaning error, not a typo |
| ١٢٣ (in a date) | — | Arabic-Indic digits are correct on screen; ASCII is not |
| هاذا · هاذه | هذا · هذه | |
| الذي (with a wrong final) | الذي · التي · الذين | check the relative pronoun agrees |

Rules and the complete table: `references/orthography.md`.

## 3 · Tashkeel

The brand floor is **0.10** (harakat ÷ letters) on any sacred text; `copy_lint` fails below it.
Above that, taste decides.

| layer | minimum | what to vocalise |
|---|---|---|
| Qurʾān | full | every letter, as in the muṣḥaf (the text is copied, never re-vocalised) |
| ḥadīth | full | as transmitted by the edition you cite |
| duʿāʾ / ziyāra | full | as transmitted |
| brand final lines, CTA | 0.18 | the ends of words, so the rhythm is readable |
| our prose (شرح، استنباط) | 0.08–0.15 | the ambiguous word only — case endings on the hinge, not on every noun |

A line that is fully vocalised at 40 px becomes a texture; a line with no tashkeel becomes a guess.
The editor's rule: **vocalise what disambiguates, leave the rest.**

Method and the 12 ambiguous forms that always get tashkeel: `references/tashkeel.md`.

## 4 · Punctuation and line breaks

- «،» between clauses, «؛» between two complete thoughts, «.» at the end of a sentence, «؟» for a
  question, «:» before a quotation.
- No space before «؟» or «،»; one space after.
- «…» is one character; «...» is three dots and is re-typed.
- A quotation is «…»; inside it, a quote is ﴿…﴾ for Qurʾān and «…» for everything else.
- Line breaks belong to the block's budget, not to the sentence: a hook is 2–6 words, a paragraph
  sentence ≤ 18 words, a step ≤ 12. Break at «،» or after a prepositional phrase, never between a
  noun and its adjective.

## 5 · The mechanical half: `ar_copycheck.py`

```bash
python3 scripts/ar_copycheck.py copy.md                 # a text file
python3 scripts/ar_copycheck.py spec.json --spec        # every on-screen field of a reel spec
python3 scripts/ar_copycheck.py copy.md --json          # machine output
python3 scripts/ar_copycheck.py copy.md --warn-only     # never exit non-zero
```

It reports, per line: tashkeel density, word count, and every hit from the tables above
(`hamza`, `ta-marbuta`, `digits`, `latin`, `bang`, `q-space`, `ellipsis`, `dialect`, `honorific`,
`sentence-long`, `quote-plain`). Exit 1 when an error is found.

**The script is not the editor.** It catches strings; it cannot tell you that a sentence is ugly, that
a metaphor is borrowed from advertising, or that the third line repeats the first. Pass 1 is yours.

## 6 · The line budget is part of the edit

The reel's blocks have hard limits (`maalsadiqeen-reel/references/blocks.md`). Editing means **cutting
to the block**, not shrinking the type:

| block | ceiling |
|---|---|
| hook line2 | 2–4 words |
| hook sub | ≤ 9 words |
| contrast right | ≤ 5 words + one `<em>` |
| answer hero | ≤ 8 words |
| paragraph sentence | ≤ 18 words (the builder splits at «،» past that) |
| definition body | ≤ 3 sentences |
| step text | ≤ 12 words |
| compare point | ≤ 8 words |
| CTA final | ≤ 7 words |

When a line does not fit, the order of fixes is: **cut the clause → move it to the caption → split
the scene**. Never: smaller font, tighter tracking, two `<em>` in one line.

## 7 · Workflow

1. Read the whole text once, aloud if possible. Mark the one sentence that carries the idea.
2. Run `ar_copycheck.py`. Fix every ✗ before touching style.
3. Pass 1 (register) on the lines that survive; delete one line in five.
4. Pass 2 (orthography), pass 3 (tashkeel) by layer, pass 4 (punctuation + breaks to the budget).
5. Run the reel's own gate: `python3 scripts/copy_lint.py spec.json`. Both green → the copy ships.

## 8 · Worked corrections

| before | after | pass |
|---|---|---|
| انشاء الله يوفقك | إِنْ شَاءَ اللهُ يُوَفِّقُكَ | orthography + tashkeel |
| هل تعرفون ما معنى الصدق | هَلْ تَعْرِفُونَ مَا مَعْنَى الصِّدْق؟ | punctuation + tashkeel |
| الإمام قال ان الصدق نجاة | قَالَ الإِمَامُ (ع): «الصِّدْقُ نَجَاةٌ» | register + attribution |
| هذا الكلام كتير مهم | هَذَا الكَلَامُ مُهِمّ | dialect + tashkeel |
| 3 خطوات لحياة أفضل | ثَلَاثُ خُطُوَاتٍ | digits + cliché |
| الصدق! | الصِّدْق | exclamation |
| والله اعلم | وَاللهُ أَعْلَم | orthography |

## 9 · Files

| path | purpose |
|---|---|
| `references/register.md` | the voice, dialect→fusha table, banned constructions |
| `references/orthography.md` | hamza rules, ta marbuta, alif maqsura, digits, the error list |
| `references/tashkeel.md` | layer-by-layer vocalisation, the ambiguous forms, density targets |
| `references/honorifics.md` | the fourteen, the exact forms, when (ع) and when عليه السلام |
| `scripts/ar_copycheck.py` | the mechanical pass (works on text or on a reel spec) |
