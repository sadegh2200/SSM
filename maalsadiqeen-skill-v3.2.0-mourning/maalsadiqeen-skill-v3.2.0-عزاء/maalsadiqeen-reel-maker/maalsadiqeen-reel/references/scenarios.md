# Scenarios — four plans, one gate

The agent no longer jumps from a brief to a build. It writes **four complete scenarios**, the user
picks one (or two), and only then does anything get built. This file defines the eight angles, the
JSON every scenario must fill, the scoring the script applies, and the rules of the gate.

```bash
python3 scripts/reel.py plan <slug>              # scaffold scenarios.json (4 empty scenarios)
python3 scripts/reel.py plan <slug> --finalize   # validate + score + preview + STOP at the gate
python3 scripts/reel.py build <slug> --choose 2  # only after the user has chosen
```

After `--finalize` the user sees `scenarios.md` (Persian table + one section per scenario) and
`preview.html` (three frames per scenario). Nothing else happens until they answer.

---

## 1 · The eight angles

Four scenarios should use **at least three different angles** and **at least two different archetypes**.
Never present four variations of the same sentence.

| # | angle (on screen: Persian, in the plan) | what it does | usual archetype | cost |
|---|---|---|---|---|
| 1 | سؤال محوری | opens with the question the text answers | A / D | M |
| 2 | تصحيح سوء فهم | names a common misreading, then corrects it calmly | C | M |
| 3 | كلمة واحدة | one word carries the whole meaning | B | S |
| 4 | تطبيق معاصر | the text applied to a situation the viewer lives | D | S |
| 5 | سلسلة السند | why this report is trustworthy (sanad, grading) | A | L |
| 6 | سيرة / لحظة | a moment from the life of the speaker or the narrator | E | S |
| 7 | سياق النصّ | what was happening when the text was said | A | M |
| 8 | ردّ شبهة بهدوء | states the objection fairly, answers with evidence | F | L |

Choose angles that fit the material. If the text has no sanad material, `سلسلة السند` is dishonest —
do not offer it to fill a quota. Three strong scenarios beat four with a filler.

## 2 · Archetypes

| code | skeleton | when |
|---|---|---|
| **A** | hook → verse → contrast → answer → proof → cta | a verse with a ḥadīth that explains it |
| **B** | hook → quote → contrast → proof → cta | a ḥadīth alone |
| **C** | hook → contrast → answer → proof/quote → cta | a concept or a scholar's point |
| **D** | hook → list/quote → answer → cta | a question with a short answer |
| **E** | title → quote/verse → answer → cta | an occasion, a person, a story |
| **F** | hook → quote (the objection) → contrast → answer → proof → cta | an objection answered calmly |
| **G** | hook → paragraph → definition → qa → cta | a chapter that explains a term in layers |
| **H** | hook → definition → compare → quote → cta | a text that defines and weighs two readings |
| **I** | hook → steps → quote → proof → cta | conditions, a procedure, an ordered practice |
| **J** | hook → timeline → quote → proof → cta | a life, a chain of transmission, a history |
| **K** | hook → compare → quote → proof → cta | a text that reports two views and chooses |
| **L** | hook → qa → quote → proof → cta | a long question, a letter, a fatwa-style passage |

`reel.py plan` reads the intake's word count: **> 700 words (or a text the intake already wants to
split) scaffolds G–L; everything shorter scaffolds A–F.** The pattern is a starting point — you may
change it, but say why in `why_fa`.

## 3 · The scenario object

`scenarios.json` is a mini-spec. Each scenario is buildable as written; `reel.py build` compiles it
into `spec.json` without inventing anything.

```json
{
  "schema": 3,
  "slug": "sadiqeen-9-119",
  "defaults": {"duration": 40, "archetype": "A", "language": "ar"},
  "scenarios": [
    {
      "id": 1,
      "title_fa": "معیّت با صادقان؛ چه کسانی؟",
      "angle": "سؤال محوری",
      "archetype": "A",
      "one_sentence": "المعية في الآية اتّباعٌ لمن عُلِم صدقه، لا مجرّد مصاحبة.",
      "hook": {"text": "كُونُوا مَعَ الصَّادِقِينَ … فَمَنْ هُم؟", "formula": 1},
      "scenes": [
        {"type": "hook", "seconds": 3.4, "lead": "«كُونُوا مَعَ الصَّادِقِينَ»",
         "line1": "فَمَنْ هُمُ", "line2": "الصَّادِقُونَ؟", "sub": "سُورَةُ التَّوْبَة · ١١٩"},
        {"type": "verse", "seconds": 10,
         "label": "﴿ سُورَةُ التَّوْبَة — ١١٩ ﴾",
         "lines": [["يَا","أَيُّهَا","الَّذِينَ","آمَنُوا","اتَّقُوا","اللهَ"],
                   ["وَكُونُوا","مَعَ","الصَّادِقِينَ"]],
         "highlight": {"words": [7, 8]}},
        {"type": "contrast", "seconds": 8.2,
         "wrong_label": "الأَمْرُ لَيْسَ:", "wrong": "مُجَرَّدَ مُصَاحَبَة",
         "right_label": "بَلْ:", "right": "مَعِيَّةُ <em>اتِّبَاع</em>",
         "line3": "مَنْ عُلِمَ صِدْقُهُ", "line4": "لَا مَنْ أَحْسَنَ الظَّنَّ بِهِ"},
        {"type": "answer", "seconds": 8,
         "q1": "سُئِلَ الإمَامُ الرِّضَا عَلَيْهِ السَّلام", "q2": "عَنْ هَذِهِ الآيَة… فَقَالَ:",
         "hero": "هُمُ الَّذِينَ صَدَّقُوا اللهَ", "after": "وَبَرُّوا رَسُولَهُ",
         "source": "— الإمام الرضا (ع) · الكافي ج١ ص٢٠٨"},
        {"type": "proof", "seconds": 9,
         "seal": ["صَحِيحُ", "السَّنَد"],
         "cards": [{"book": "الكافي", "loc": "ج١ / ص٢٠٨", "grade": "بِسَنَدٍ صَحِيح"}],
         "line1": "سَنَدٌ يَثْبُتُ", "line2": "لَا يُقَالُ بِالظَّنّ",
         "attribution": "— العلّامة المجلسي · مرآة العقول ج٢ ص٤٢١"},
        {"type": "cta", "seconds": 6.4,
         "line1": "وَكُونُوا مَعَ", "line2": "الصَّادِقِينَ <em>اليَوْم</em>",
         "share": "أَرْسِلْهَا لِمَنْ تُحِبّ", "final": "وَكُونُوا مَعَ الصَّادِقِينَ",
         "brand": {"handle": "@maalsadiqeen"}}
      ],
      "needs": {"recitation": "9:119", "proof": ["الكافي ج١ ص٢٠٨"], "assets": []},
      "life_impact": "لا تنسب قولاً إلى الله قبل أن تعرف سنده؛ ارجع إلى النصّ أولاً.",
      "risk": "low",
      "cost": "M",
      "why_fa": "مستندترین روایت با سند صحیح؛ برای مخاطب پژوهشگر قوی‌ترین شروع."
    }
  ]
}
```

### Fields

| field | required | rule |
|---|---|---|
| `id` | ✓ | unique integer; survives re-ordering |
| `title_fa` | ✓ | short Persian title for the menu, not for the screen |
| `angle` | ✓ | one of the eight above, spelled as written |
| `archetype` | ✓ | A–F |
| `one_sentence` | ✓ | ≤ 14 words; if it takes more, it is two ideas |
| `hook.text` | ✓ | 4–8 words, scored ≥ 65, no forbidden wording |
| `hook.formula` | ✓ | 1–12 from `references/hooks-ar.md`; used by the diversity guard |
| `scenes` | ✓ | 5–8 blocks, first `hook`, last `cta`, sum 30–50 s (hard ≤ 60) |
| `scenes[].seconds` | ✓ | 2.5–12 per block |
| `needs.recitation` | verse | `surah:ayah`; it sizes the verse scene |
| `needs.proof` | proof | one string per expected source card |
| `life_impact` | ✓ | the «الأثر في الحياة» line; 4–32 words, a deed not a slogan |
| `risk` | ✓ | `low` / `medium` / `high` — high is fine if named honestly |
| `cost` | ✓ | `S` / `M` / `L` — assets + research time |
| `why_fa` | ✓ | one Persian sentence: why this scenario is worth the user's choice |

### Blocks and timing

| block | typical s | what it must carry |
|---|---|---|
| `hook` | 3.0–4.5 | one question, one number/condition, one stake — word on screen ≤ 1.2 s |
| `verse` | 8–14 | the āyah, fully vocalised, highlight ≤ 2 words |
| `quote` | 8–12 | the ḥadīth, vocalised, attribution with book/volume/page |
| `contrast` | 6–9 | what it is **not** vs. what it is — one `<em>` hinge |
| `answer` | 7–9 | the decisive line; one hero per reel |
| `proof` | 7–9 | book + volume + page; a seal **only** with a stated grading |
| `list` | 8–10 | ≤ 3 items, each ≤ 7 words |
| `title` | 3–4 | the occasion or the name, not a summary |
| `paragraph` | 10–16 | one passage, 2–4 sentences, kicker + source |
| `definition` | 9–13 | term + one `حدّ` + one note |
| `steps` | 11–15 | 2–4 ordered acts, ≤ 12 words each |
| `timeline` | 12–16 | 2–4 moments with an ear-date |
| `compare` | 11–15 | two columns × ≤ 3 points + a verdict |
| `qa` | 12–18 | a question and a 2–5 sentence answer |
| `cta` | 6–7 | approved share line + final line + brand card |

**The word budget scales with the duration.** Sum every word that appears on screen (not the
sources, not the labels): soft `max(95, 2.3 × seconds)`, hard `max(110, 2.9 × seconds)`. A 40 s reel
holds ~95; a 53 s long-text reel ~122. If the copy exceeds it, cut a sentence — **never shrink the
font** and never pad the caption to compensate.

A prose block is budgeted from the same number: `max(1.80, 0.30 × words + 0.55) + 0.18` per sentence.
If `validate` says a block is short for its prose, extend the scene or cut a sentence; the builder
prints the same warning at `--finalize` time (`last reveal … 0.9 s before the end`).

## 4 · Scoring (handled by `scenarios.py score`)

| component | max | how it is earned |
|---|---|---|
| hook | 40 | `hook_score_ar.py` score × 0.40 (brevity, curiosity, stakes, second person, specificity, structure, dignity) |
| evidence | 20 | a card with a stated grading = 20 · a card/reference without one = 14 · no source = 4 |
| clarity | 15 | one-sentence ≤ 14 words, known block types, hook first + CTA last, every block 2.5–12 s |
| freshness | 15 | −6 if the angle appeared in the last 2 reels, −4 if the archetype in the last 3, −5 if the hook formula in the last 5 |
| cost | 10 | `S` = 10 · `M` = 7 · `L` = 3 |

Total 0–100. Nothing below 65 should be offered unless the material is genuinely thin — and then say
so in the plan instead of padding the list.

## 5 · What `validate` enforces

Hard errors (the gate will not open):

- fewer than three scenarios, duplicate ids, missing `title_fa` / `one_sentence` / `life_impact`;
- a hook missing, or containing forbidden wording;
- an unknown block type, a non-positive duration, total > 60 s;
- an empty scene list, first block not `hook`, last block not `cta`;
- a `proof` seal with no stated grading anywhere in its cards (invented authority);
- fewer than three distinct angles.

Warnings (print, judge, usually fix): hook outside 4–8 words, one-sentence > 14 words, total outside
the preferred window (30–50 s; 42–58 s for the long-text archetypes G–L), another scenario with the same hook, a proof block whose cards do not match `needs.proof`,
ASCII digits in a reference, an angle repeat from the last two reels, an archetype outside A–L, and a
long-text block whose prose needs more seconds than its scene has (`words / 3.3 + 1.6`).

## 6 · Presenting the plan (Persian, one message)

```
۴ سناریو آماده است. هر کدام یک ریل کامل و قابل ساخت است:

| # | زاویه | وعده | مدت | هزینه | امتیاز |
|---|---|---|---|---|---|
| ۱ | سؤال محوری | … | ۴۰ ث | M | ۸۵ |
| ۲ | تصحیح سوء فهم | … | ۳۸ ث | S | ۷۷ |
...

پیش‌نمایش سه فریم از هر سناریو: preview.html

کدام را بسازم؟ «۱» — یا «۱ و ۳» برای دو نسخه.
```

Attach or open the preview. Do not describe all four in prose; the table is the menu.
If the user hesitates, recommend one and say why in a single sentence.

## 7 · The gate

- Do **not** run `build` before the user names a scenario. There is no "build all four to see".
- If the user says «همه», build them as separate deliveries, one at a time, and say how long each takes.
- If the user asks for changes to a scenario, edit `scenarios.json` and re-run `--finalize`
  (validate + score + preview) — then ask again. Do not hand-edit a `spec.json` that the gate produced.
- If the user picks two, build both; the second is an A/B, not a replacement.

## 8 · Variants

A/B is a change to scene 1 only, not to the idea:

```bash
python3 scripts/scenarios.py variant <slug> --id 2 --hook "هوك جديد قصير؟" --out $W/variant-2.json
```

Keep the same body. Publish the A/B as two reels or as Trial Reels; judge on 3-second watch and
sends-per-reach, never on likes (`references/platforms.md`).

## 9 · Diversity guard

`scenarios.py score` reads `config/content-log.json` (the last 10 entries). `reel.py build` appends
one entry per built reel. Never delete history: the log is how the page avoids repeating itself.
