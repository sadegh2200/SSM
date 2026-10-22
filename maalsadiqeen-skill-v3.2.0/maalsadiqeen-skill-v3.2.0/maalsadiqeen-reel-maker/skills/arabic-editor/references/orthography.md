# Orthography — what the checker checks, and why

Arabic copy fails on a small number of repeated points. This file is the rule set behind
`ar_copycheck.py`; when the script and a native speaker disagree, the speaker wins and this file is
corrected.

## 1 · Hamza

| position | rule | example |
|---|---|---|
| initial, pronounced | write أ / إ | أَكْرَمَ · إِكْرَام |
| initial, hamzat waṣl | no hamza written (or ٱ in the muṣḥaf) | ابْتِدَاء · اسْتِغْفَار · اجْتِمَاع · انْتِظَار |
| medial on wāw | when the vowel before it is ḍamma | مُؤْمِن · سُؤَال |
| medial on yāʾ | when the vowel before it is kasra | بِئْر · مِئَة |
| medial on the line | after a sukūn or a long vowel | مَسْأَلَة · يَسْأَل · قُرْآن |
| final, after a long vowel | on the line | شَيْء · دُعَاء · سَمَاء |
| final, after a short vowel | on a seat | مَرْأَة · لُؤْلُؤ |

**The five errors that keep appearing:** «مسئلة» (→ مسألة), «شئ» (→ شيء), «إبتداء» (→ ابتداء),
«إنشاء الله» (→ إن شاء الله), «اللة» (→ الله).

Rule of thumb for hamzat waṣl: if the word is a maṣdar of a Form VII–X verb or a definite article,
there is no written hamza at the start of the line: اسْتِقَامَة، انْتِصَار، اجْتِهَاد، الانْتِبَاه.

## 2 · Tāʾ marbūṭa and hāʾ

- A feminine noun ends in **ة**: رَحْمَة، نِعْمَة، حِكْمَة، سُنَّة، جَنَّة، عِبْرَة، كَلِمَة.
- A pronoun suffix ends in **ه**: رَحْمَتُهُ، نِعْمَتُهُ، كِتَابُهُ.
- «الله» is written with a tāʾ-shaped hāʾ (ه) that is never a ة.
- In a construct, the tāʾ is pronounced and written: رَحْمَةُ اللهِ — not رَحْمَة الله (the ة stays).

The checker flags «اللة», and flags a curated list of words written with ه that must carry ة only
when they are **not** followed by a pronoun suffix — because «رحمه» is a correct word.

## 3 · Alif maqṣūra and yāʾ

| word | final | meaning |
|---|---|---|
| عَلَى | ى | on, upon |
| عَلِي | ي | the name |
| هُدَى | ى | guidance |
| رَضِيَ | ي | he was pleased |
| إِلَى | ى | to |
| فِي | ي | in |

A final ى is written without dots in Naskh and Kufi; a final ي carries them. Mixing them changes the
word, so the checker reports every «علي» that is followed by a place or a preposition («علي الأرض» →
«على الأرض»).

## 4 · Numbers

- On screen, digits are **Arabic-Indic**: ٠١٢٣٤٥٦٧٨٩. A reference, a year, a page, a count.
- ASCII digits 0–9 are a styling error in Arabic copy; `copy_lint` warns, `ar_copycheck` errors on a
  reference line.
- Dates: «سَنَة ١٤٨ هـ» — with the هـ, not «148 هـ».
- A number at the start of a sentence is written in words: «ثَلَاثَةُ أُمُورٍ» not «٣ أمور».

## 5 · Punctuation

| mark | use | note |
|---|---|---|
| ، | between clauses | no space before it |
| ؛ | between two complete thoughts | rarer than in English |
| . | end of a sentence | the page uses few full stops on screen |
| ؟ | question | no space before it |
| : | before a quotation or a list | «قَالَ (ع):» |
| «…» | a quotation | the closing » after the last letter |
| ﴿…﴾ | Qurʾān only | never for a ḥadīth |
| … | ellipsis, one character | never three dots |

In RTL text a parenthesis opens on the right: «(ع)» wraps the honourific, and the closing paren sits
on the left of the letter it follows — the renderer handles it; do not type mirrored brackets.

## 6 · The error table `ar_copycheck.py` enforces

| wrong | right |
|---|---|
| إنشاء الله | إن شاء الله |
| انشالله | إن شاء الله |
| اللة | الله |
| مسئلة | مسألة |
| شئ | شيء |
| إبتداء / إبتدأ | ابتداء / ابتدأ |
| إستغفار / إستغفر | استغفار / استغفر |
| إجتماع / إجتمع | اجتماع / اجتمع |
| إنتظار / إنتظر | انتظار / انتظر |
| الإمامة (as إمامة inside a word) | — (only the standalone word) |
| هاذا / هاذه | هذا / هذه |
| الذى / التى | الذي / التي |
| عبدالله | عبد الله |
| علية (for عليه) | عليه |

Suffixes and prefixes matter: the checker matches whole words, so «إستغفار» inside a sentence is
caught while «مُسْتَغْفِر» is not.

## 7 · What is never normalised

- A verse or a ḥadīth: transcribed exactly, including its own punctuation.
- A scholar's quotation: exactly, including an unusual spelling, if the edition has it.
- A name: as the person is known (المجلسي، الكليني، الصدوق، المفيد، الطوسي).
- The book titles: الكافي، من لا يحضره الفقيه، تهذيب الأحكام، بحار الأنوار، نهج البلاغة — with their
  own orthography.
