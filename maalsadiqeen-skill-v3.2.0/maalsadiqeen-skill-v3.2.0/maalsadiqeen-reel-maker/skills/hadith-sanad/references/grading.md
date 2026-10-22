# Grading — the vocabulary of درجة الحديث

A grading is a **legal opinion about a chain**, not a fact about the text. Two scholars can grade the
same report differently, and both can be right within their method. That is why the page prints the
grader's name with the word.

## 1 · The terms

| term | literal | what it means in Imami usage | seal |
|---|---|---|---|
| صحيح | sound | the chain is connected and every narrator is an Imami `ثقة` (trustworthy, explicitly praised) | ✓ |
| حسن | good | the chain is connected, the narrators are Imami but praised without an explicit `توثيق` | ✓ |
| موثق | reliable | the chain is connected, the narrators are trustworthy but not Imami (or their madhhab differs) | ✓ |
| قوي | strong | like موثق but the trustworthiness comes from a weaker source | ✓ (rare) |
| معتبر | considered | a later scholar's judgement that the report can be relied on, even if the chain is not formally صحيح | ✓, in its own word |
| مقبول | accepted | accepted by the community of scholars, without a formal chain judgement | ✓ only with the grader |
| ضعيف | weak | a narrator is unreliable, or the chain is broken | ✗ |
| مرسل | loose | the chain omits a generation (usually the Imam is quoted directly by a later narrator) | ✗ |
| منقطع | cut | a link is missing in the middle | ✗ |
| معضل | knotty | two or more consecutive links are missing | ✗ |
| مضمر | implicit | the report does not name the Imam («عَنْهُ» / «عَنْ أَحَدِهِمَا») | ✗ |
| موضوع | fabricated | judged a forgery | ✗ (never on this page) |

## 2 · The traps

| trap | why it matters | what to do |
|---|---|---|
| «صحيح» used as a synonym for «true» | it is a technical judgement | keep the word for the chain, and only with a grader |
| upgrading «معتبر» to «صحيح» | two different claims | keep the source's word |
| «صحيح الإسناد» vs «صحيح» | some scholars distinguish the chain from the report's acceptance | keep the exact phrase |
| a Sunni grading applied to an Imami chain | different rijal systems | either find an Imami grader or leave the grade empty |
| a website's grade | not a citation | find the book; if you cannot, `needs_verification` |
| «متفق عليه» | Bukhārī/Muslim agreement, a Sunni category | never for an Imami report |
| a dream or a sermon quoted as ḥadīth | genre confusion | label it «مِنْ كَلَامِ …» or «فِي خُطْبَةٍ» |
| نهج البلاغة | a compilation of sermons and letters, not a musnad | no seal, no chain claim |

## 3 · What a grader looks like on screen

```
— الكافي ج١ / ص٢٠٨ · بِسَنَدٍ صَحِيح
— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١
```

Two lines: the **source** and the **grader**. If the second line does not exist, the word «صحيح» does
not appear.

In a `proof` block:

```json
"cards": [{ "book": "الكافي", "loc": "ج١ / ص٢٠٨", "grade": "بِسَنَدٍ صَحِيح",
            "graded_by": "العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١", "status": "from_input" }],
"seal": ["صَحِيحُ", "السَّنَد"],
"attribution": "— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١"
```

The seal repeats the card; it never says more than the card says.

## 4 · The four statuses, and what each one allows

| status | meaning | may quote | may seal |
|---|---|---|---|
| `from_input` | the reference was in the material | ✓ | only if the material also states a grading |
| `verified` | you opened a real edition this session and saw the page | ✓ | only with a stated grading |
| `needs_verification` | the quote is real-looking, the reference is missing or doubtful | ✓ with a caption note | ✗ |
| `unverified_text` | the wording itself is uncertain | ✗ until the user confirms | ✗ |

`needs_verification` is not a failure. It is the honest state of most of what arrives by WhatsApp, and
the caption says so in one calm line: «سَنَدُ هَذِهِ الرِّوَايَةِ لَمْ يُذْكَرْ فِي المَصْدَرِ الَّذِي
وَصَلَنَا».

## 5 · The chain, when the reel is about the chain

`timeline` block, one event per generation:

| when | text |
|---|---|
| الطَّبَقَة الثَّالِثَة | «عَنْ أَبِي عَبْدِ اللهِ (ع)…» — the Imam |
| الطَّبَقَة الرَّابِعَة | the first narrator, and what the rijāl books say of him |
| الطَّبَقَة الخَامِسَة | the next link |
| التَّدْوِين | «الكافي · الكليني · القرن الثالث» |

Only what the rijāl books say is printed — «قَالَ النَّجَاشِيّ: ثِقَةٌ» — never «ثقة» on your own
authority. If the material does not include the chain, the reel is not about the chain.
