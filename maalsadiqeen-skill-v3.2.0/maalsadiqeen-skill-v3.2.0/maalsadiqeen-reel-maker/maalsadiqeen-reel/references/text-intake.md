# Text intake — any text, any length, into a brief

The input is no longer a set of sheets. It can be a page of notes, a chapter of a book, a lecture
transcript, a forwarded message, a question from a follower, or five photographs of a printed page.
The job of this step is to **understand** the material and write a brief — not to produce a reel yet.

Script: `scripts/intake.py` does the mechanical half (normalise, count, extract quotes + references,
classify, suggest a shape). The other half is yours: read it, decide the one idea, write `brief.md`.

```bash
python3 scripts/intake.py <file|dir|-> --slug <slug> [--sheets a.jpg b.jpg] [--source-policy hybrid]
# → $REEL_WORK/<slug>/{input.txt, brief.seed.json, brief.seed.md}
# then write $REEL_WORK/<slug>/brief.md yourself, using the template in §7
```

---

## 1 · What you may and may not do to the text

| may | may not |
|---|---|
| fix line order left by OCR, remove page headers, join split words | rewrite, shorten or "improve" a verse or a ḥadīth |
| normalise whitespace, unify quote marks | translate a quotation into Persian and quote the translation as the text |
| correct an obvious typo in the author's own prose (mark it in the brief) | correct sacred text from memory — ever |
| merge repeated paragraphs | drop a reference because it is inconvenient |
| flag an unreadable word as `[؟]` and ask | silently supply a word that "must" be there |

If the input is an image of a page, transcribe it exactly as printed, then run the same checks.
If a sacred text appears twice with a difference, treat it as an uncertainty and ask.

## 2 · Segment into units of thought

A **unit** is one complete idea that could stand alone: a verse + its explanation, one ḥadīth + its
lesson, one objection + its answer, one story, one definition.

- Split on headings, blank lines, and changes of subject.
- Merge paragraphs shorter than ~40 words into the neighbouring unit.
- A unit longer than ~450 words is usually two units; look for the seam.
- Every unit keeps its own quotes and references — never let a reference float to the wrong unit.

`intake.py` prints the units with word counts; you confirm or correct the split in `brief.md`.

## 3 · Quotes, references, and the status of each

Four kinds of quotation, each with its own layer:

| kind | marker in the input | layer | on screen |
|---|---|---|---|
| `quran` | ﴿…﴾, «…» after «قال الله», `(التوبة: ١١٩)` | **نصّ** | fully vocalised, ﴿ ﴾, sūrah + āyah |
| `hadith` | «…» after «قال الإمام / رسول الله / عن…», `الكافي ج١ ص٢٠٨` | **نصّ** | vocalised, with the book, volume, page |
| `scholar` | «…» after a scholar's name, or a named commentary | **شرح** | the scholar's name is on screen |
| `other` | an unsourced sentence quoted in the material | **استنباط** | never shown as a quotation |

Rules for the reference:

- Record it exactly as written: `الكافي ج١ ص٢٠٨`, `نهج البلاغة، الحكمة ٣١`, `بحار الأنوار ج٢ ص٣`.
- Arabic-Indic digits on screen (٠١٢٣٤٥٦٧٨٩), never ASCII.
- A grading (`صحيح السند`, `معتبر`, `مرسل`, `ضعيف`) is quoted only if the input states it **or** a
  named scholar states it in the input. Otherwise the field stays empty and no seal is shown.
- `status` is one of:
  - `from_input` — the reference was in the material;
  - `verified` — you checked it against a real edition this session;
  - `needs_verification` — the quote is real-looking but the reference is missing or doubtful.

**A ḥadīth with `needs_verification` never gets a proof seal.** It can still be the subject of the reel,
with the source card showing only what is known, or with no source card at all.

## 4 · Source policy

`config/brand.json → defaults.source_policy` (default `hybrid`):

| policy | meaning |
|---|---|
| `input` | only what the material says; ask the user for every missing reference |
| `research` | look up references the material omitted, from real editions, and mark them `verified` |
| `hybrid` | default — use the material; research only sacred text and only when it can be verified; ask for the rest |

When researching: prefer the primary book, then a recognised commentary. Never cite a website as the
source of a ḥadīth; a website may help you find the page, the citation is the book.
If a search does not settle it in a few minutes, mark it `needs_verification` and move on.

## 5 · Classify (A–F)

Classification decides the skeleton, not the topic.

| class | signature in the text | archetype |
|---|---|---|
| **A** | a verse **and** a ḥadīth (or a graded report) that explains it | آية + حديث |
| **B** | a ḥadīth alone, with a reference | حديث فقط |
| **C** | a scholar's point, a definition, a concept | فكرة / تصحيح مفهوم |
| **D** | a question with a short answer | سؤال وجواب |
| **E** | a date, a person, an occasion | مناسبة / سيرة |
| **F** | an objection or a claim to answer calmly | ردّ شبهة |

If the material mixes two classes, choose the one that carries the *strongest single idea*; the other
becomes a second scenario (see `scenarios.md`) or a second reel in the series.

The class says **what the text is**; the length says **which skeleton carries it**. A 1200-word
chapter whose class is C is still built from G–L (prose blocks), not from a 40-second contrast reel.

## 6 · Decide the shape

| words in the material | shape | what to do |
|---|---|---|
| ≤ 250 | one reel | one idea, 30–40 s |
| 250–700 | one reel, richer caption | the caption carries what the screen cannot |
| 700–1800 | one reel **or** 2–3 parts | split only if there are 2–3 independent ideas |
| > 1800 | series | 3–8 parts, each with its own idea and its own reel |

The screen budget scales with the reel: **soft 2.3 words/second, hard 2.9** — ~95 on-screen words for
a 40 s reel, ~122 for a 53 s one. Everything else belongs in the caption, the comments, or the next
part. Never solve a long text by shrinking the font, and never split a sentence to make the word
count look smaller.

When the text is 700–1800 words and still one idea, the prose blocks (`paragraph`, `definition`,
`qa`, `steps`, `timeline`, `compare`) are how it fits: one dense block carries 25–40 words at reading
speed, and the rest of the reel stays short. See `narrative.md` G–L.

## 7 · Write `brief.md` (Persian, for the user)

Use exactly these headings; keep it short enough to read on a phone.

```markdown
# بریف — <slug>

## ایدهٔ واحد
<یک جمله، ≤ ۱۴ کلمه. اگر نمی‌توانی، متن دو ایده دارد.>

## چرا این ایده
<۲–۳ خط: چه چیزی در متن تازه است، چه برداشتی را اصلاح می‌کند.>

## نقل‌قول‌ها
| # | لایه | متن | منبع | وضعیت |
|---|---|---|---|---|
| q1 | نصّ | ﴿…﴾ | التوبة ١١٩ | from_input |
| q2 | نصّ | «…» | الكافي ج١ ص٢٠٨ | needs_verification |

## لایه‌ها
- **نصّ:** …
- **شرح:** … (از <نام عالم>)
- **استنباط ما:** …

## الأثر في الحياة
<یک تغییر مشخص در هفتهٔ مخاطب؛ فعل، نه شعار.>

## شکل پیشنهادی
<یک ریل / دو ریل / مجموعهٔ ۴ قسمتی> — چون <دلیل>.

## سه سؤال (فقط اگر لازم است)
1. …
```

## 8 · When to ask, and when not to

Ask **at most three** questions, in one message, and only about things that change the output:

1. a sacred text whose wording is uncertain in the input;
2. a ḥadīth with no reference when the proof block is essential to the idea;
3. whether a long text should become a series.

Do not ask about: hook wording, colours, length (the brand decides), or "should I make it?".
If the material is enough, say so and move to the plan.

## 9 · Hand-off

`intake.py` wrote `brief.seed.json`. `brief.md` is yours. The next step is
`python3 scripts/reel.py plan <slug>` — it reads the seed and scaffolds four scenarios.
