---
name: hadith-sanad
description: Use before any ḥadīth, report, sanad, grading (صحيح، حسن، موثق، ضعيف، مرسل) or «proof» card is written on screen or in a caption for «مع الصادقين» — and whenever a quoted saying needs its متن, its سند, its تخريج and its درجة recorded, or when `copy_lint` / `sanad_check.py` reports an invented seal, a missing grading or a malformed reference. Triggers on «سند», «تخریج», «درجه حدیث», «این روایت معتبر است؟», "is this hadith authentic", "add the reference", and on any proof block with a seal.
license: Proprietary — made for the maalsadiqeen page.
metadata:
  title: Sanad discipline — علم السند والتخريج
  version: 1.0.0
  scope: quoted ḥadīth, their chains, gradings, citations and the proof card
  pairs_with: maalsadiqeen-reel (proof block), arabic-editor (the copy of the quote)
---

# Sanad discipline — متن · سند · تخريج · درجة

The page's authority is borrowed, never manufactured. A ḥadīth on screen is four things at once:
the **متن** (the words), the **سند** (who heard it from whom), the **تخريج** (where it is written), and
the **درجة** (how strong it is). If one of the four is missing, the reel says so — it never fills the
gap with confidence.

> **The one rule that overrides every other rule in this repository:** a grading is quoted, never
> inferred. If no named scholar graded this report in the material you were given, the seal is not
> printed. Not «صحيح السند» and not «معتبر» — nothing.

## 1 · The five steps

| # | step | output |
|---|---|---|
| 1 | **Identify the متن** — the exact words, vocalised, with no paraphrase | a string you can compare character by character |
| 2 | **Find its place** — book, volume, page (or ḥadīth number) as the material gives it | a citation, or `needs_verification` |
| 3 | **Record the سند** if the material has it — the chain is content, not decoration | a chain line, or "chain not in the source" |
| 4 | **Quote the درجة** only if stated, and name who stated it | `grade` + `graded_by` |
| 5 | **Decide the card** — what the proof block may show | `cards`, `seal` or no proof block |

```bash
python3 scripts/sanad_check.py card.json          # validate one card
python3 scripts/sanad_check.py spec.json --spec   # validate every quote/proof in a reel spec
python3 scripts/sanad_check.py notes.md           # a draft: transmitted «…» with no citation is flagged
```

## 2 · What a proof card may contain

```json
{
  "book": "الكافي",
  "loc": "ج١ / ص٢٠٨",
  "grade": "بِسَنَدٍ صَحِيح",
  "graded_by": "العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١",
  "status": "from_input"
}
```

| field | rule |
|---|---|
| `book` | the work as it is named in the edition: الكافي · من لا يحضره الفقيه · تهذيب الأحكام · بحار الأنوار · نهج البلاغة · وسائل الشيعة |
| `loc` | Arabic-Indic digits, «ج» before the volume and «ص» before the page; نهج البلاغة uses «الخطبة ٣١» / «الكتاب ٥٣» / «الحكمة ٣١» |
| `grade` | one of the vocabulary in `references/grading.md`, in the words the grader used |
| `graded_by` | the scholar and the work where the grading appears — required whenever `grade` is set |
| `status` | `from_input` · `verified` · `needs_verification` |

The proof block prints `book` + `loc` on the card, `grade` only inside the card, and `graded_by` in
the attribution line. A seal («صَحِيحُ السَّنَد») is printed **only** when a card has a non-empty
`grade` **and** `graded_by`, and `status != needs_verification`.

## 3 · The seal rules

| situation | seal | what the screen says |
|---|---|---|
| graded صحيح by a named scholar, reference complete | ✓ «صَحِيحُ السَّنَد» | book · loc · the grader in the attribution |
| graded حسن / موثق / معتبر | ✓ with its own word | never upgraded to صحيح |
| the grading is in the material but the grader is unnamed | ✗ | «بِسَنَدٍ ذَكَرَهُ …» or no seal |
| no grading anywhere | ✗ | book · loc only |
| `needs_verification` | ✗ | the reel may still quote it — with a caption note |
| a weak report used as a warning, not a proof | ✗ | «رُوِيَ» and no seal |

A seal with no grading is an **invented authority** and fails `copy_lint` (`invented-seal`). There is
no exception for a report you are sure about.

## 4 · When the source is missing

In order:

1. **Look in the material.** The user often pasted the reference further down.
2. **Research the sacred text only** (Qurʾān and well-known ḥadīth), and mark `verified` only if you
   actually opened a real edition this session. A website may help you find the page; the citation is
   the book.
3. **Ask once**, in the same message as your other questions: «این روایت در منبعی که فرستادید سند
   ندارد؛ منبعش را دارید؟»
4. **Ship without the seal**, with the card showing only what is known, and say it in the Persian
   summary. An unsealed but honest reel is publishable; a sealed guess is not.

Never: invent a page, round a volume, cite a commentary as the primary source, or write «متفق عليه»
for an Imami report.

## 5 · The chain (سند) on screen

The page rarely prints a full chain — it prints the **result** of the chain (the grading) and keeps the
chain in the caption or in a series episode about the sanad (`references/series.md` of the reel skill).

If the reel is *about* the chain (angle «سلسلة السند»), the `timeline` block is the right shape: one
event per link, `when` = the generation («الطَّبَقَة الثَّالِثَة»), text = the narrator and what is known
about him. The repertoire of narrator-criticism (توثيق/تضعيف) is quoted from كتب الرجال — النجاشي،
رجال الطوسي، رجال الكشي، خلاصة العلامة — never from memory.

## 6 · Vocabulary you may print

Full definitions and the Imami usage of each term: `references/grading.md`. The short list:

`صحيح` · `حسن` · `موثق` · `قوي` · `معتبر` · `مقبول` · `ضعيف` · `مرسل` · `منقطع` · `معضل` · `مضمر` ·
`موضوع`

Two rules for use:

- **Never translate a grading into a stronger one.** «معتبر» is not «صحيح»; «موثق» is not «حسن».
- **Never print a term the source did not use.** If the material says «رواية معتبرة», the card says
  «معتبرة», not «صحيحة».

## 7 · Worked cards

| material | card | seal |
|---|---|---|
| «الكافي ج١ ص٢٠٨» + «بسند صحيح» | book الكافي · loc ج١ / ص٢٠٨ · grade بِسَنَدٍ صَحِيح · graded_by = whoever said it | ✓ |
| «الكافي ج١ ص٢٠٨» with no grading | book · loc · grade "" | ✗ |
| «روي عن الإمام الصادق (ع)» | no book → no proof block; quote labelled «رُوِيَ» | ✗ |
| «بحار الأنوار ج٢ ص٣، عن الكافي» | book بحار الأنوار · loc ج٢ / ص٣ · grade "" ; the chain note in the caption | ✗ |
| «نهج البلاغة، الحكمة ٣١» | book نهج البلاغة · loc الحكمة ٣١ | ✗ (نهج البلاغة is not a musnad) |

## 8 · Files

| path | purpose |
|---|---|
| `references/grading.md` | the vocabulary, what each term means, who uses it, and the traps |
| `references/citation.md` | book-by-book citation shapes, Arabic-Indic digits, edition notes |
| `scripts/sanad_check.py` | validates a card, a whole spec, or a plain-text draft (text mode warns on an uncited transmitted saying and on ASCII digits); exits 1 on an invented seal |
| `assets/card.example.json` | a complete, valid card to copy |
