# Citation — how a reference is written on this page

A reference is written **once**, in one shape, and reused everywhere: proof card, caption, comment
bank, alt text. Arabic-Indic digits, «ج» for volume, «ص» for page, «ح» for the ḥadīth number when the
edition has one.

## 1 · The standard shape

```
<book> ج<volume> / ص<page>            or      <book> ج<volume> / ص<page> · ح<number>
```

```
الكافي ج١ / ص٢٠٨
تهذيب الأحكام ج٢ / ص٣٤٥ · ح٧١
من لا يحضره الفقيه ج١ / ص٢٠٨
بحار الأنوار ج٢ / ص٣
```

- A space before and after the slash is the page's house style; «ج١/ص٢٠٨» is accepted in a caption
  where space is short.
- Never «ج 1» — the number is attached to «ج» and written in Arabic-Indic digits.
- Never «ص. ٢٠٨» or «صفحة ٢٠٨» on screen; the card is terse.

## 2 · نهج البلاغة

Not a musnad: it is cited by part, not by page.

```
نهج البلاغة · الخطبة ٣١
نهج البلاغة · الكتاب ٥٣
نهج البلاغة · الحكمة ٣١
```

No volume, no page, no seal. The compiler (الشريف الرضي) may be named in the caption, not on the card.

## 3 · The books the page actually uses

| book | author | shape | note |
|---|---|---|---|
| الكافي | الكليني (ت ٣٢٩ هـ) | ج / ص / ح | the four-volume editions differ; keep one edition per series |
| من لا يحضره الفقيه | الصدوق (ت ٣٨١ هـ) | ج / ص / ح | often cited by ḥadīth number |
| تهذيب الأحكام | الطوسي (ت ٤٦٠ هـ) | ج / ص / ح | |
| الاستبصار | الطوسي | ج / ص / ح | |
| بحار الأنوار | المجلسي (ت ١١١٠ هـ) | ج / ص | a compilation — cite the earlier source when it is named |
| وسائل الشيعة | الحرّ العاملي (ت ١١٠٤ هـ) | ج / ص + أبواب | «ج١ / ص٢٠ · بَابُ …» |
| مستدرك الوسائل | النوري (ت ١٣٢٠ هـ) | ج / ص | |
| غرر الحكم | الآمدي | رقم | «غرر الحكم · ح٣٤» |
| الأمالي | الصدوق / الطوسي | المجلس / ص | |
| كامل الزيارات | ابن قولويه | ج / ص | |
| مصباح المتهجّد | الطوسي | ص | duʿāʾ and ziyāra |

Commentaries are cited in the attribution, with their own volume and page:

```
— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١
— المازندراني · شرح أصول الكافي ج٣ ص١٢
```

## 4 · Grading and citation together

```
الكافي ج١ / ص٢٠٨ · بِسَنَدٍ صَحِيح
— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١
```

The first line is the **source**; the second is the **grader**. If there is no second line, the word
«صحيح» is not printed (`grading.md` §3).

## 5 · Digits

| use | form |
|---|---|
| volume, page, ḥadīth number | ٠١٢٣٤٥٦٧٨٩ |
| a year | ١٤٨ هـ · ٢٠٢٥ م |
| a surah:āyah | ٩:١١٩ (Arabic-Indic, colon between) |
| a count in prose | words: «ثَلَاثَةُ أَحَادِيث» |

ASCII digits in a reference are an error (`sanad_check.py` exits 1). In a URL or a handle they are
fine — those are not Arabic copy.

## 6 · What is never cited

- A search engine, a Telegram channel, a PDF without a title page.
- «مصادر شيعية» or «كتب الحديث» as a book name.
- A volume without a page, unless the work is organised by ḥadīth number.
- A commentary as if it were the primary text («قال المجلسي» for a ḥadīth is not a citation of the
  ḥadīth).
- A page number you did not see. Write `needs_verification` and say it in the summary.

## 7 · The caption version

The caption may carry more than the card:

> «الكافي، ج١، ص٢٠٨ — بِسَنَدٍ صَحِيح ذَكَرَهُ العلّامة المجلسي في مرآة العقول ج٢ ص٤٢١.»

Same numbers, same order, more words. The card on screen stays terse; the caption explains.
