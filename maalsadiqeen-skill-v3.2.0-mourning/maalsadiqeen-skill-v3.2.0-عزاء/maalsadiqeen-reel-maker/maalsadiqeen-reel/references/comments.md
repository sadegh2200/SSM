# Comments — seven slots, written before publishing

A reel is published with its comment bank already written. The comments do the work the video cannot:
hold the full reference, start the conversation, define the term, land the life-impact, point to the
next part, answer the objection before it is shouted, and ask for the send.

```bash
python3 scripts/comments.py spec.json --out comments.md [--at 19:30] [--series series.json]
```

`comments.py` derives every line from the spec (never invents a source), checks each one (≤ 300 chars,
no emoji, no «!», Arabic, no duplicates, the pinned one carries a reference) and schedules it in the
audience's time zone with the UTC equivalent.

---

## 1 · The seven slots

Times are offsets from the publish moment (`config/brand.json → comments.offsets_minutes`).

| # | slot | at | job | rule |
|---|---|---|---|---|
| 1 | **المصادر والدرجة** | +0 min | the full reference, the grading, the text | **pinned**; the only comment with a real citation; ≤ 300 chars |
| 2 | **سؤال الافتتاح** | +20 min | start the thread with a question answerable in one line | no yes/no; quote the hero if it helps |
| 3 | **توضيح المصطلح** | +2 h 30 | define the one term a non-specialist will trip on | ≤ 70 chars per idea; no lecture |
| 4 | **الأثر في الحياة** | +2 h 30 | the deed from the reel, restated as a comment | one sentence, no slogan |
| 5 | **سؤال الحلقة القادمة** | +5 h | harvest the next reel's question | ask for a topic, not for praise |
| 6 | **ردّ استباقي هادئ** (objection) | +24 h | answer the predictable objection from the source | never argue; quote and stop |
| 7 | **دعوة للمشاركة** | +24 h | ask for the send, once | approved share line only |

Two slots at +2 h 30 is intentional: the term and the life-impact are read by different people —
the one who did not understand, and the one who understood but did not act.

## 2 · The pinned comment

- It is the only place with the complete reference: `الكتاب جX صY` + grading + the text itself.
- Write it as three short parts: `المصادر:` / `الدرجة:` / `النصّ:`.
- Pin it immediately after publishing; it is the comment a sceptic looks for.
- If there is **no** reference, the pin becomes «المصدر: يُذكر عند التحقّق» — do not invent one.
  Better: do not publish a proof reel without a source at all.

Example:

```
المصادر: الكافي ج١ / ص٢٠٨ (بِسَنَدٍ صَحِيح). الدرجة: صَحِيحُ السَّنَد.
النصّ: «يَا أَيُّهَا الَّذِينَ آمَنُوا اتَّقُوا اللهَ وَكُونُوا مَعَ الصَّادِقِينَ».
```

## 3 · Tone in the replies

- Reply once, calmly, with the source. Never twice to the same provocation.
- A hostile comment answered with a reference is content; answered with sarcasm it is a fight.
- Delete only: insults, spam, personal data. Do not delete a fair objection — answer it in slot 6
  and let it stay.
- If a comment corrects a real mistake in the reel: say so publicly, fix the caption or the pinned
  comment, and note it in the next reel. That is the brand's strongest move.
- Persian speakers get a Persian reply; the public thread stays Arabic.

## 4 · What not to write

| no | why |
|---|---|
| «تابعونا» / «لايك» / «شاركوا» | follow-bait; the brand never begs |
| a second pinned comment with a link | links belong in the bio or the first comment only |
| a copy-paste of the caption | the comment must add something |
| a promise («من قرأها…») | invented authority |
| a debate with a named sect | not the page's voice |
| emoji, «!!», all caps | not the register |

## 5 · Timing rules

- Publish inside the window (`references/platforms.md`); the schedule starts at that minute.
- Comment 1 within the first minute, then pin it.
- Comment 2 after ~20 minutes, when the first wave of viewers has arrived.
- The +2 h 30 pair catches the second wave; the +5 h question catches the evening.
- The +24 h pair is the day-after maintenance — the objection comment works while the reel still
  circulates, and the share request is the last honest ask.
- Do not schedule comments on all three platforms with the same text; Facebook wants the question,
  X rarely needs a comment at all (reply to yourself only to add the reference).

## 6 · Measuring the comments

- A question comment that gets ≥ 5 real answers is a validated topic: plan a reel on it.
- An objection comment that gets hostile replies tells you the hook was too sharp; soften the framing.
- The pinned comment's saves are a proxy for "this reel is worth keeping".
