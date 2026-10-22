# Honorifics — the fourteen, and how they are written

The page names the Prophet and the Imams often. A missing or wrong honourific is the fastest way to
lose a reader's trust, and `copy_lint` warns on every name it finds without one.

## 1 · The table

| # | name on screen | short form | full form (a line by itself) |
|---|---|---|---|
| 1 | النَّبِيّ مُحَمَّد | ﷺ or (ص) | صَلَّى اللهُ عَلَيْهِ وَآلِهِ وَسَلَّم |
| 2 | الإِمَام عَلِيّ | (ع) | عَلَيْهِ السَّلَام |
| 3 | فَاطِمَة الزَّهْرَاء | (ع) | عَلَيْهَا السَّلَام |
| 4 | الإِمَام الحَسَن | (ع) | عَلَيْهِ السَّلَام |
| 5 | الإِمَام الحُسَيْن | (ع) | عَلَيْهِ السَّلَام |
| 6 | الإِمَام زَيْن العَابِدِين / السَّجَّاد | (ع) | عَلَيْهِ السَّلَام |
| 7 | الإِمَام البَاقِر | (ع) | عَلَيْهِ السَّلَام |
| 8 | الإِمَام الصَّادِق | (ع) | عَلَيْهِ السَّلَام |
| 9 | الإِمَام الكَاظِم | (ع) | عَلَيْهِ السَّلَام |
| 10 | الإِمَام الرِّضَا | (ع) | عَلَيْهِ السَّلَام |
| 11 | الإِمَام الجَوَاد | (ع) | عَلَيْهِ السَّلَام |
| 12 | الإِمَام الهَادِي | (ع) | عَلَيْهِ السَّلَام |
| 13 | الإِمَام العَسْكَرِيّ | (ع) | عَلَيْهِ السَّلَام |
| 14 | الإِمَام المَهْدِيّ | (عج) | عَجَّلَ اللهُ فَرَجَهُ الشَّرِيف |

## 2 · When to use which form

| place | form | why |
|---|---|---|
| attribution line («— الإمام الصادق (ع) · الكافي ج١ ص٢٠٨») | (ع) | a page reference is not a sermon |
| a full line that names the Imam as the speaker | عَلَيْهِ السَّلَام | the line is read aloud |
| the frame where the Imam speaks (hero, quote label) | once, at the end | repeating it on every line is noise |
| the Prophet | ﷺ on screen; «صَلَّى اللهُ عَلَيْهِ وَآلِهِ وَسَلَّم» when the line has room | the page's default is the full form on a standalone line |
| the Mahdi | (عج) | the page does not print the full form inside a sentence |

**One honourific per name, per line.** Two honourifics in one line («الإمام الصادق عليه السلام (ع)») is
a typo, and `copy_lint` counts the characters, not the intent.

## 3 · Spelling

- «الإِمَام» with hamzat qaṭʿ and the kasra; «الامام» without the hamza is an orthography error.
- «عَلَيْهِ السَّلَام» — two words, no «و» between them, no final «و» on السلام.
- «صَلَّى اللهُ عَلَيْهِ وَآلِهِ وَسَلَّم» — «وآلِهِ» is part of the page's form; never drop it for space,
  drop the line instead.
- «(ع)» — Arabic parentheses, no space before, one space after.
- «عَجَّلَ اللهُ فَرَجَهُ» — «فرجه» with a hāʾ, not a tāʾ marbūṭa.

## 4 · Names that are not the fourteen

| case | form |
|---|---|
| a companion (صَحَابِيّ) | رَضِيَ اللهُ عَنْهُ — but the page rarely names companions |
| a scholar (الكليني، الصدوق، المجلسي، المفيد، الطوسي) | رَحِمَهُ الله / رَضِيَ اللهُ عَنْهُ — or nothing; the name alone is respectful |
| a narrator in a sanad | the name alone, with «عَنْ» before it |
| a living person | no honourific |

Do not invent an honourific for a scholar whose title you are not sure of. The name is enough.

## 5 · The checker

`ar_copycheck.py` looks for the fourteen names and, within 60 characters after the name, for one of:
`(ع)`, `(عج)`, `عليه السلام`, `عليها السلام`, `عليهما السلام`, `صلى الله عليه`, `صلى الله عليه وآله`,
`ﷺ`, `رضي الله عنه`, `رحمه الله`. A name with none of them is a warning; a name inside a reference
line (`source`, `attribution`) is exempt when it is a book title.

`copy_lint` runs the same check on the rendered spec and warns; the editor fixes the line before the
build, not after.
