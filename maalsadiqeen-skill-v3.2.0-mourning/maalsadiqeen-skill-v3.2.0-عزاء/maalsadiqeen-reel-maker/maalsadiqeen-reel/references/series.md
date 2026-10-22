# Series — when one reel is not enough

A long text is not a long reel. When the material holds more than one idea, the honest answer is a
series of short reels, each with its own opening, its own source and its own life-impact.

`intake.py` proposes the shape; `scenarios.py` can scaffold the parts; `reel.py build` builds them one
at a time. A series is still built reel by reel — never as one 3-minute file.

## 1 · When to split

Split when **two or more** of these are true:

- the material has more than one independent idea (each could stand alone);
- on-screen copy would exceed the reading budget of one reel (`max(110, 2.9 × seconds)` words);
- the sanad material alone is a full story;
- the text raises a term that needs its own explanation;
- the user asks for a full lecture or a chapter.

Do **not** split:

- to make a single idea feel bigger;
- to game the algorithm with cliffhangers — this audience dislikes it and the brand forbids it;
- when part 2 would be padding. Two strong parts beat five thin ones.

## 1b · When *not* to split, even though the text is long

A 700–1800-word text with **one** idea is one reel built from G–L, not a three-part series. The prose
blocks carry the density (`narrative.md`, `blocks.md` §Long form); a series of three parts that each
repeat the same idea is worse than one 50-second reel that lands it.

Split when the ideas are independent; keep it whole when they are layers of the same idea.

## 2 · Anatomy of a part

Every part must be understandable **on its own** (someone will see part 3 first).

| element | rule |
|---|---|
| opening | the same 1.5 s signature (paper texture + the small «مع الصادقين» line), then a complete hook |
| identity | `الجزء الثاني من ثلاثة` in the kicker, in Arabic-Indic digits |
| source | every part carries a reference — never «انظر الجزء الأول» |
| idea | one idea per part, named in the first 5 seconds |
| ending | a CTA + a bridge to the next part **as a question**, not a tease |
| consistency | same tokens, same fonts, same motion personality as a standalone reel |

## 3 · Naming

- On screen: `الجزء الأول · الثاني · الثالث` (never 1/2/3 in ASCII).
- Caption: `من سلسلة «<عنوان السلسلة>» — الجزء الثاني`.
- Filename: `<slug>-p2.mp4`.
- The series title is a noun phrase, not a question: «معية الصادقين» not «هل تعرف من هم الصادقون؟».

## 4 · `series.json`

```json
{
  "slug": "maaiyat-al-sadiqin",
  "title_ar": "معيّة الصادقين",
  "title_fa": "معیّت با صادقان",
  "parts": [
    {"n": 1, "idea": "من هم الصادقون؟", "question": "ما معنى المعية في الآية؟", "scenario_id": 1},
    {"n": 2, "idea": "المعية اتّباع لا مصاحبة", "question": "هل يكفي حسن الظنّ؟", "scenario_id": 2},
    {"n": 3, "idea": "كيف نكون معهم اليوم", "question": "ما الذي نفعله غداً؟", "scenario_id": 3}
  ],
  "cadence_days": 3,
  "cover": "same paper, part number in the kicker"
}
```

`comments.py --series series.json` uses `parts[].question` for comment slot 5, so the next part is
announced with a real question instead of a promise.

## 5 · Calendar

- 2–4 parts, 3 days apart (the same account should not publish two series at once).
- Part 1 is the strongest idea, not the introduction. The audience decides on part 1.
- Announce nothing before part 1 is live; announce part 2 only in the comment of part 1.
- If part 1 underperforms (watch < 40 %), stop the series and rebuild part 2 as a standalone; do not
  drag a weak opening through four parts.

## 6 · Consistency

- Same brand card, same watermark, same closing beat.
- Same hook formula family within one series (e.g. question → question → condition) and a different
  one in the next series.
- Same length ±5 s, so the series feels like a format.
- The series ends with an explicit last part (`الجزء الثالث والأخير`) and a CTA to the next topic —
  never an open-ended «يتبع».

## 7 · Ending a series

Close with the part that answers the question the first part asked. Then:

- pin a comment that lists the three parts with their references;
- publish a carousel (optional) with the three hero lines;
- log the series in `config/content-log.json` so the diversity guard does not repeat the angle for a
  month.
