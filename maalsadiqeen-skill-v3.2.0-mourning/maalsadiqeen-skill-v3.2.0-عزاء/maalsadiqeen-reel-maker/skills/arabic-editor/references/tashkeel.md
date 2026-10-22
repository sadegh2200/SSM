# Tashkeel — how much, where, and for whom

Tashkeel in this brand is **a reading instruction, not a decoration**. It tells a reader who knows
Arabic which of two readings is meant, and it tells a reader who is rusty that the page respects the
text enough to punctuate it.

`copy_lint` computes density as `harakat ÷ base letters` and fails sacred text below **0.10**. The
editor works with four layers:

| layer | floor | rule |
|---|---|---|
| Qurʾān | as printed | never re-vocalise; copy from the muṣḥaf text you were given |
| ḥadīth | as printed | copy from the edition; if the edition is unvocalised, mark it and ask |
| duʿāʾ / ziyāra | 0.10 | as transmitted |
| brand finals, CTA, hook lead | 0.18 | the ends of words, so the line scans |
| our prose (شرح، استنباط) | 0.08 | the ambiguous word only |

## 1 · What always gets tashkeel in our prose

1. The hinge word — the one the `<em>` marks anyway.
2. A word that changes meaning with the case: «إِنَّ» vs «أَنَّ», «مَنْ» vs «مِنْ».
3. A passive that could be read as active: «كُتِبَ» vs «كَتَبَ».
4. A verb whose past and imperative look alike: «عَلِمَ» / «اعْلَمْ».
5. A name that could be misread: «الحَسَن» vs «الحُسَيْن» is unambiguous in script, but «الحسن» alone
   needs its vowels to be the name rather than the adjective.
6. The first word of a sentence that begins with a hamza: «إِنَّ», «أَنَّ», «إِذَا».
7. A word ending in tāʾ marbūṭa followed by a pronoun: «رَحْمَتُهُ» — the ḍamma is the grammar.

## 2 · What stays bare

- Long connectives: «وَمِنْ ثَمَّ»، «لِذَلِكَ» — one vowel each is enough.
- Repeated words in a list: the first occurrence carries the tashkeel, the rest do not.
- A word already unambiguous in context: «الكِتَاب» in a sentence about a book.
- Our own prose in a `paragraph`: tashkeel on the hinge and the first word, nothing else. A fully
  vocalised paragraph at 40 px is unreadable — the eye loses the word boundaries.

## 3 · The 12 ambiguous forms

| form | reading | when |
|---|---|---|
| إِنَّ | indeed | emphasis |
| أَنَّ | that | after a verb of saying or knowing |
| أَنْ | to | before a verb |
| مَنْ | who | interrogative or relative |
| مِنْ | from | preposition |
| عَنْ | about | preposition |
| أَمْ | or | after a question |
| أَوْ | or | otherwise |
| لَا | no | negation |
| لَ | indeed | emphatic prefix |
| كَلِمَة | a word | noun |
| كُلِّمَ | he was spoken to | passive verb |

A line that contains one of these without its vowel is a line that will be read wrong by someone.
That is the whole test.

## 4 · Density targets by block

| block | target | why |
|---|---|---|
| `verse` | as printed (~0.35–0.50) | the muṣḥaf |
| `quote` (ḥadīth) | as printed or ≥ 0.25 | the reader must hear the case endings |
| `answer` (Imam's words) | ≥ 0.25 | it is a quotation |
| `definition` term | ≥ 0.15 | one word, read twice |
| `paragraph` | 0.08–0.15 | read once, for meaning |
| `steps`, `timeline` | 0.08–0.15 | short lines, verbs only |
| `compare` cells | 0.08 | the verdict carries the vowels |
| CTA `final` | ≥ 0.18 | the line is remembered |

## 5 · Method

1. Write the sentence without tashkeel.
2. Read it aloud twice: once as a reader who knows the subject, once as one who does not.
3. Mark the word where the two readings diverge. That word gets the vowels.
4. If the sentence is sacred, do not mark anything — copy it.
5. Run `ar_copycheck.py`; it reports density per line and flags a quoted span with none.

## 6 · Two failures to avoid

- **Over-vocalising our prose** so that the page looks like a grammar book and the reading slows to a
  crawl. Density above 0.30 in a `paragraph` is a warning in review, not a badge.
- **Under-vocalising a quotation** so that the reader supplies the wrong case. A quote at 0.05 is a
  misquotation waiting to happen; `copy_lint` fails it below 0.10.

The test is not «does it look traditional» but «can it be read aloud, once, without a mistake».
