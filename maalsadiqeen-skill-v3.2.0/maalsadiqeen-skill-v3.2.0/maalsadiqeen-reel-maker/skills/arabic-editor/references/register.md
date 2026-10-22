# Register — the voice of «مع الصادقين»

One voice, four constraints: **classical, calm, scholarly, addressable**. Every line is read by a
35–60-year-old reader in Iraq, Lebanon, the Gulf or the diaspora who knows the vocabulary of the
tradition and has no patience for a slogan.

## 1 · The four constraints

| constraint | what it means on the page | what it forbids |
|---|---|---|
| classical | فصحى with the case endings the meaning needs; the vocabulary of the commentaries | dialect, loanwords, «لغة الشارع» |
| calm | one claim per line; no escalation; no exclamation | «انتبه!», «صدمة», «لن تتوقع» |
| scholarly | a name, a book, a page for every claim; «وَمِنْ ذَلِكَ» marks our inference | «قال العلماء» without a name |
| addressable | the reader is spoken to, not lectured at; «تَأَمَّلْ» not «أنت جاهل» | second-person shaming, rhetorical traps |

## 2 · Dialect → fusha

The list `ar_copycheck.py` enforces (word-boundary match; extend it only with evidence from the page's
own comments):

| dialect | fusha | note |
|---|---|---|
| كتير / كتيرة | كثير / كثيرة | |
| شو | ماذا | |
| ليش | لِمَاذَا | |
| هيك | هَكَذَا | |
| هلق / هلأ | الآن | |
| منيح | حَسَن | |
| بدي | أُرِيد | |
| بدك | تُرِيد | |
| مو | لَيْسَ | |
| كمان | أَيْضًا | |
| بس | لَكِنْ / فَقَطْ | context decides |
| شي | شَيْء | |
| هيدا / هاد | هَذَا | |
| عم (بـ + verb) | the simple imperfect | «عم يحكي» → «يَحْكِي» |
| تعا | تَعَالَ | |

Lebanese and Iraqi forms differ; when a word is ambiguous, use the classical equivalent rather than
picking a dialect.

## 3 · Banned constructions (they appear in religious short-form video constantly)

1. «هل تعلم أن…؟» — a schoolroom opening, not a question.
2. «لا أحد يخبرك بهذا» / «ما يقال لك» — conspiracy framing.
3. «توقف عن…» / «لا تفعل…» — shaming.
4. «٩٩٪ من الناس لا يعرفون» — invented statistics.
5. «السرّ الذي…» — clickbait.
6. «سنة ٢٠٢٥» as a stake — the brand is not news.
7. «ستُصدم» / «لن تتوقع» — promise of shock.
8. «أقسم بالله» in our own voice — we do not swear.
9. «قال الإمام» without «(ع)» — see `honorifics.md`.
10. «الأحاديث» as a synonym for «الروايات» in Imami material — the technical word is رواية/خبر.
11. «الفرقة الناجية» and any labelling of other Muslims — the page does not do polemics.
12. Numbers as decoration («٣ أسرار», «٧ حقائق») unless the text itself counts.
13. «حياة أفضل» / «طاقة إيجابية» — the life-impact clichés `copy_lint` rejects.
14. «في هذا الفيديو» / «في هذا الريل» — the reel does not describe itself.
15. «اشترك» / «تابعنا» as the first CTA — the CTA is a take-away, not a subscribe plea.
16. «إعجاب وشارك» — no engagement begging; the share line is a sentence.
17. Emoji, kaomoji, decorative brackets ❰❱.
18. Latin transliteration on screen («Imam al-Sadiq») — the Arabic name is the name.
19. The passive that hides the actor («يُقال») when a name is known.
20. «الجدير بالذكر» and other filler connectives — cut them.

## 4 · Sentence shape

- Prefer the verb-first sentence: «قَالَ الإِمَامُ…» not «الإمام قال…».
- One subordinate clause per sentence. If there are two, there are two sentences.
- A definition is one sentence; an explanation is three; a paragraph is never five.
- The hinge of a line is one word, and `<em>` is spent on it once.
- A question ends with «؟»; a statement never ends with «…» unless it is a quotation.

## 5 · The three layers, in the voice

| layer | marker in copy | never |
|---|---|---|
| نصّ (verbatim) | «…», ﴿…﴾, with a reference | paraphrased, shortened, re-vocalised |
| شرح (a named scholar) | «قَالَ …» / «ذَهَبَ … إِلَى» | «قال العلماء» without a name |
| استنباط (ours) | «وَمِنْ ذَلِكَ…»، «وَيُفْهَمُ مِنْهُ…» | dressed as a quotation |

A sentence in the third layer that sounds like the first is the most serious copy error the page can
make. If the reader cannot tell who is speaking, the line is rewritten.

## 6 · Length by block

The budget lives in `maalsadiqeen-reel/references/blocks.md`; the editor's short version:

| block | words |
|---|---|
| hook line2 | 2–4 |
| hook sub | ≤ 9 |
| contrast side | ≤ 5 |
| answer hero | ≤ 8 |
| quote line | ≤ 7 |
| paragraph sentence | ≤ 18 |
| step | ≤ 12 |
| compare point | ≤ 8 |
| CTA final | ≤ 7 |

Cut in this order: the adjective, the connective, the repetition, the clause. If the line still does
not fit, the scene is wrong, not the sentence.
