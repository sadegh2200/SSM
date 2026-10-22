# Writing the on-screen Arabic (فصيح، متين، قابل للانتشار)

> **Captions and X posts use the same register** with different lengths: the caption is prose
> (نصّ → شرح → استنباط → أثر), the X post is one claim. Platform limits and skeletons live in
> `references/platforms.md`; `scripts/captions.py` enforces them and refuses follow-bait.

The audience is educated Arabic speakers who will notice a wrong ḥaraka faster than a wrong colour.
Write like a careful editor of a religious quarterly who also knows what stops a thumb.

## Register

- Classical Arabic (فصحى التراث) with full vocalisation on sacred and quoted text; modern standard for
  labels. No dialect, no loanwords, no «!» , no emojis, no English except the handle.
- Sentence length on screen: 2–6 words per line, ≤ 3 lines per reveal. If a line needs a comma, split it.
- Prefer nominal sentences for conclusions («التَّقْوَى طَرِيق») and verbal ones for narration
  («سُئِلَ الإمَامُ …»). Avoid «و» at line starts except inside a quoted text.
- Build tension with structure, not adjectives: question → negation («لَيْسَ …») → affirmation («بَلْ …»)
  → consequence. Never editorialise («مذهل», «صادم», «لن تصدّق»).

## Quoting

- Verses: Uthmani spelling as in the Muṣḥaf, inside ﴿ ﴾ when labelled, or « » inside running text.
  Always sūrah name + āyah number in Arabic-Indic digits: «سُورَةُ التَّوْبَة — ١١٩».
- Ḥadīth: quote verbatim; ellipsis «…» only between complete clauses; attribution line format:
  «— الإمام الرضا (ع) · الكافي ج١ ص٢٠٨». The speaker is named with «عَلَيْهِ السَّلام» the first time.
- Scholars: «— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١». Titles: العلّامة، الشيخ، السيّد، المحقّق — as the
  tradition uses them; never bare surnames.
- Grading vocabulary (use only what the sheet or a source states): صحيح السند، معتبر، موثّق، حسن،
  مرسل، ضعيف. Never upgrade a grading to make the seal possible — drop the seal instead.

## Tashkeel checklist (the usual errors)

- Case endings on the last word of a line that ends a sentence are optional *only* in prose labels;
  mandatory inside verses and ḥadīth.
- Shadda before the vowel on the same letter: «الصَّادِقِينَ» not «الصَادِّقِينَ». Double-check ـيـن/ـون
  endings: «الصَّادِقُونَ» (nominative) when subject, «الصَّادِقِينَ» (accusative/genitive) after «مَعَ».
- Hamza: «الأَئِمَّة», «سُئِلَ», «آمَنُوا», «أُنَاسٌ». Alif maqṣūra vs yāʾ: «عَلَى», «إِلَى».
- Sun letters: «الصَّادِقُون», «التَّقْوَى», «السَّنَد» carry the shadda; moon letters do not («الأَئِمَّة»).
- Final hamza/tāʾ marbūṭa in attributions: «الآيَة», «مَعِيَّة», «غَايَة».
- Interrogative «؟» is the Arabic mark, no space before it.

## Markup available in the spec

- `<em>word</em>` → gold, 1.18 em (one per line, the hinge word).
- Words of a `verse` block are a list — split on spaces, keep «يَا أَيُّهَا» as one token when it must
  animate together.
- `quote.reveal: "words"` for ≤ 14-word texts that deserve a word-by-word rhythm; `"lines"` otherwise.

## Line budget per block (keeps the frame breathing)

| block | field | max words | max base chars |
|---|---|---|---|
| hook | lead / line1 / line2 / sub | 4 / 3 / 2 / 6 | 24 / 14 / 12 / 36 |
| verse | per visual line | 6 | 34 (auto-wraps beyond) |
| contrast | wrong / right / line3 / line4 | 4 / 5 / 3 / 7 | 22 / 26 / 18 / 40 |
| answer | q1 / q2 / hero / after / source | 6 / 5 / 4 / 4 / 9 | 36 / 30 / 22 / 24 / 48 |
| proof | card / line1 / line2 / attribution | 6 / 4 / 4 / 9 | 40 / 22 / 22 / 48 |
| quote | per line / attribution | 7 / 9 | 40 / 48 |
| list | item | 7 | 40 |
| cta | line1 / line2 / share / final | 3 / 5 / 4 / 5 | 16 / 28 / 24 / 28 |

`build_reel.py` shrinks fonts to fit, but shrinking below the minimum sizes is a *writing* failure —
cut words instead.

## Caption (الوصف) skeleton — 3–5 lines + 3–5 keywords, no hashtag walls

```
﴿…﴾ — سورة …، الآية …
سُئل الإمام … (ع) عن الآية فقال: «…» [المصدر ج ص]
… (one line: the idea in plain words)
أرسلها لمن تحبّ، واحفظها للعودة.
#مع_الصادقين #الإمام_الرضا #تفسير #حديث
```
