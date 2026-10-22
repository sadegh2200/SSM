# Narrative patterns & beat sheets (30–60 s, default 40 s)

> Archetypes are chosen **before** the build and presented as scenarios. Since v3 the agent never
> picks one silently: `references/scenarios.md` turns the material into four scored menus and the
> user chooses. This file is what you open once the choice is made.

Every reel keeps the same spine:

> **hook → the text → the explanation → the turn → the authority → the take-away**

What changes with the length of the input is **how much of that spine is spoken in prose**. Short
inputs (A–F) carry one idea per scene. Long inputs (G–L) put a passage on screen in a `paragraph`,
`definition`, `qa`, `steps`, `timeline` or `compare` block, and keep every other scene short.

## The first rule: one idea per reel

A reel is not a summary. It is one sentence the viewer can repeat after 40 seconds.

- ≤ 250 words of input → one reel, 30–40 s, archetype A–F.
- 250–700 words → one reel, 38–50 s; the caption carries what the screen cannot.
- 700–1800 words → **one reel from G–L** (the prose blocks absorb the density) *or* 2–3 parts if the
  text holds 2–3 independent ideas.
- > 1800 words → a series (`references/series.md`), 3–8 parts, each with its own idea and its own reel.

The screen budget is not negotiable: **soft 2.3 words per second, hard 2.9** (`copy_lint.py`). When a
sentence does not fit, it moves to the caption, the comment bank, or the next part.

## Universal pacing

- First cut ≤ 4.5 s; the big hook word is on screen by 1.2 s.
- Short-form lines: ≥ 1.15 s + 0.26 s/word. Prose sentences: ≥ 1.80 s + 0.30 s/word.
- No frame static for more than 3.4 s — 5.0 s inside a prose block (a sentence is being read).
- One hero moment between 50–65 % of the runtime — the frame people screenshot.
- Last 6–7 s = CTA: take-away + share line + brand card; the card holds ≥ 1.5 s.
- Every sacred text on screen is vocalised, referenced, and never reworded.

---

# Short-form patterns (A–F)

## A · سؤال → جواب المعصوم (verse + ḥadīth + grading) — 45 s, six scenes

| # | block | s | content | cues |
|---|---|---|---|---|
| 1 | hook | 0–3.4 | lead = the verse fragment; line1 «فَمَنْ هُمُ»; line2 the subject with «؟»; sub = sūrah · āyah | emphasis 1.9 |
| 2 | verse | 3.4–13.2 | the āyah word by word with the recitation; highlight the hinge words | words from `cues.py`, highlight ≈ last word + 0.6 |
| 3 | contrast | 13.2–21.6 | «الأَمْرُ لَيْسَ: …» struck / «بَلْ: … <em>hinge</em>» / consequence / second consequence | wrong +0.3, strike +1.4, right +2.4, line3 +4.2, line4 +5.4 |
| 4 | answer | 21.6–29.6 | q1 «سُئِلَ الإمَامُ …», q2 «عَنْ هَذِهِ الآيَة… فَقَالَ:», hero, after, source | hero ≈ +3.0 |
| 5 | proof | 29.6–38.6 | seal «صَحِيحُ / السَّنَد», 1–2 cards, scholar line1/line2, attribution | seal +0.8, cards +2.0/+3.1 |
| 6 | cta | 38.6–45 | line1 (2–3 words), line2 with `<em>`, share, final = the verse fragment, brand | final ≈ end − 2.3 |

Example: `assets/examples/sadiqeen-9-119.silent.json`.

## B · كلمة واحدة تغيّر المعنى (a ḥadīth that turns on one word) — 42 s

1. **hook** (0–3.4): lead = 3–4 words of the ḥadīth; line1 «مَاذَا تَعْنِي»; line2 the hinge word.
2. **quote** (3.4–12): the ḥadīth, `reveal: "words"`, label, attribution.
3. **contrast** (12–20): wrong reading (strike) vs right reading with `<em>` + consequence.
4. **quote** `hero: true` (20–28): the decisive clause alone; attribution with ج/ص.
5. **proof** (28–36): seal if graded; cards; scholar line(s).
6. **cta** (36–42).

No verse → no recitation; sound design + bed only.

## C · تصحيح مفهوم (correcting a common notion) — 40 s

1. **hook**: line1 «يَظُنُّ كَثِيرُون» / line2 the notion; sub «وَالنَّصُّ يَقُولُ غَيْرَ ذَلِك».
2. **contrast**: the notion (strike) vs the text's wording (`<em>`), then «الفَرْقُ: …».
3. **quote** `hero: true`: the text that settles it.
4. **list** (optional, 3 items max): what follows from the correction.
5. **proof** (cards only, no seal unless a graded ḥadīth).
6. **cta**.

## D · سؤال → جواب (FAQ) — 36–45 s

hook (the question, line2 = the 1–2 word core) → **title** «الجَوَاب» kicker + one line → **quote**
or **list** (the answer, ≤ 3 items) → **proof** (one card) → **cta**. The answer scene ≥ 8 s.
If the answer needs three sentences rather than three items, use **L** instead of D.

## E · مناسبة (occasion) — 30–36 s

**title** (kicker = date «١٣ رجب», title = the name, sub = one line) → **quote** (`reveal: "words"`,
with recitation if it is a verse) → **quote** `hero` (the one line to remember) → **cta** (final =
«عَظَّمَ اللهُ أُجُورَكُم» / «مُبَارَكٌ عَلَيْكُم»). No contrast block — occasions are not arguments.

## F · ردّ شبهة (answering an objection) — 45–50 s

hook (the objection stated fairly, as a quoted question) → **contrast** (objection struck, the text's
claim in gold) → **quote** hero (the decisive text) → **proof** (cards + scholar) → **list** (2–3
consequences, optional) → **cta** (final = the sacred text, never a jab).

---

# Long-form patterns (G–L)

These six are for the 700–1800-word text. They are also useful for a short text that happens to be
**prose** rather than a quotation — a follower's question, a scholar's two paragraphs, a definition.

The rule that keeps them watchable: **one dense block per reel is the anchor; the rest is short.**
Two dense blocks only when the reel is ≥ 45 s and they are the argument (term → comparison). Never
three paragraph-length scenes in one 40-second reel.

## G · شرحٌ متدرّج (progressive exposition) — 47–54 s

The text explains a word or an idea in layers. Reveal the layers in the order a good teacher would.

| # | block | s | content |
|---|---|---|---|
| 1 | hook | 3.4 | the word in the viewer's own question («مَا يَعْنِي الصِّدْق؟») |
| 2 | paragraph | 13–14 | the first layer: what the language says, 2–3 sentences, kicker «فِي اللُّغَة» |
| 3 | definition | 12–13 | the term itself, one `حدّ`, one note |
| 4 | qa | 14–16 | the objection the viewer is already forming, answered in 3 sentences |
| 5 | cta | 7 | take-away + share + brand |

Measured: `assets/examples/long-text-sadiq.silent.json` — 53.5 s, 5 scenes, 0 lint failures.

**Fails when** the paragraph and the definition say the same thing. Layer two adds *why*, not a
synonym.

## H · تعريفٌ ثمّ مقارنة (the word, then two readings) — 41 s

hook (3.4) → **definition** (9.5) → **compare** (13) → **quote** hero (9) → **cta** (6.4).

The definition fixes the word; the comparison shows what people think it means versus what the text
means; the quote settles it. Use when the input itself contrasts two understandings.

**Fails when** `col_a` becomes a straw man. Write the strongest version of the common reading, then
let the text answer it.

## I · خطوات (an ordered practice) — 40 s

hook (3.4) → **steps** 3–4 (13) → **quote** hero (9) → **proof** (7.5) → **cta** (6.4).

Use when the text gives a procedure, conditions, or a sequence of acts. Each step is an action in ≤ 12
words, and the step heads are «أَوَّلًا / ثَانِيًا / ثَالِثًا» — not sentences.

**Fails when** the steps are really a list of virtues. If nothing is ordered, use `list`.

## J · خطّ زمني (a life, a chain, a history) — 42 s

hook (3.4) → **timeline** 3–4 (15) → **quote** hero (9) → **proof** (7.5) → **cta** (6.4).

For a biography, the transmission of a report, or the history of a practice. `when` is written for the
ear. The last event must point at the viewer's present («اليَوْم»), otherwise the reel is a museum.

**Fails when** the events are not comparable — a year, a century and a slogan in one rail.

## K · مقارنة هادئة (two positions, weighed) — 39–41 s

hook (3.4) → **compare** (13) → **quote** hero (9) → **proof** (7.5) → **cta** (6.4).

For a text that reports two views and then chooses. The verdict line says what the text settles — it
never says who is foolish. If the material names a group, the column heads stay descriptive
(«الظَّنُّ الشَّائِع» / «النَّصُّ»), not accusatory.

**Fails when** the verdict is our opinion rather than the text's — mark it as ours
(«وَمِنْ ذَلِكَ…») or cut it.

## L · سؤالٌ طويل (a real question, answered in full) — 41–45 s

hook (3.4) → **qa** (14–16) → **quote** hero (9) → **proof** (7.5) → **cta** (6.4).

The most faithful shape for a follower's question, a letter, or a fatwa-style passage. The `qa`
answer is 2–5 sentences of plain fusha, no lists, no slogans; the `quote` that follows is the
evidence, not a repeat of the answer.

**Fails when** the qa answer quotes the ḥadīth that the next scene quotes. Answer first, prove after.

---

## The ending, per archetype

The last scene is not decoration; it is the last thing the reader keeps. One invitation at most
(`references/brand-voice.md` §9):

| archetype | ending | why |
|---|---|---|
| A · verse + ḥadīth | احْفَظْهَا لِلْعَوْدَةِ | the reader will want the reference again |
| B · one word | احْفَظْهَا لِلْعَوْدَةِ | a definition is a thing to keep |
| C · correcting a notion | أَرْسِلْهَا لِمَنْ سَأَلَكَ عَنْهَا | someone is already asking this |
| D · FAQ | أَرْسِلْهَا لِمَنْ سَأَلَكَ عَنْهَا | the question has an asker |
| E · occasion | **none** | a mourning or feast reel is not a campaign |
| F · objection | **none** | an argument is not sold; it is left standing |
| G · progressive exposition | احْفَظْهَا لِلْعَوْدَةِ | the reader returns to the passage |
| H · definition → comparison | أَرْسِلْهَا لِمَنْ سَأَلَكَ عَنْهَا | the distinction answers a real confusion |
| I · steps | احْفَظْهَا لِلْعَوْدَةِ | a practice is done again next week |
| J · timeline | **none** | a life or a chain ends on its own weight |
| K · calm comparison | أَرْسِلْهَا لِمَنْ سَأَلَكَ عَنْهَا | two readings, one settled question |
| L · long question | أَرْسِلْهَا لِمَنْ سَأَلَكَ عَنْهَا | the answer belongs to whoever asked |

## Choosing the pattern

| the input looks like | pattern | why |
|---|---|---|
| a verse + a ḥadīth explaining it | A | the recitation is the spine |
| one ḥadīth whose meaning turns on a word | B | the word is the hinge |
| a concept someone misreads | C | the contrast carries the turn |
| a short question from a follower | D | one answer, one screen |
| a date, a person, an occasion | E | no argument, just the day |
| an objection, stated fairly | F | answer with evidence, no polemic |
| a chapter that explains a term | G | layers, in teaching order |
| a text that defines and compares | H | word → readings → text |
| a text with conditions or acts | I | order matters |
| a life, a chain, a history | J | time is the structure |
| a text that weighs two views | K | the verdict is the payoff |
| a long question / a letter | L | answer in full, then prove |

## Hook formulas that fit this brand (from the ig-reel skill, filtered for dignity)

The full table of 12 formal-Arabic formulas, the writing rules and the three-hook routine are in
`hooks-ar.md`; score candidates with `scripts/hook_score_ar.py` (publish ≥ 65, aim ≥ 80).

| formula | pattern | example |
|---|---|---|
| Open question on a known text | «‹قطعة من النص› … فَمَنْ/فَمَا/فَلِمَاذَا …؟» | «كُونُوا مَعَ الصَّادِقِينَ» … فَمَنْ هُمُ الصَّادِقُون؟ |
| Condition → consequence | «إِذَا كَانَ … فَـ…؟» | إِذَا كَانَتِ التَّقْوَى فَرِيضَة، فَمَعَ مَنْ أَمَرَكَ اللهُ أَنْ تَكُون؟ |
| One word | «كَلِمَةٌ وَاحِدَةٌ تُغَيِّرُ المَعْنَى» + the word | كَلِمَةٌ وَاحِدَة: مَعَ |
| Common assumption | «يَظُنُّ كَثِيرُونَ أَنَّ …» | يَظُنُّ كَثِيرُونَ أَنَّ الصِّدْقَ صِفَةٌ فَقَط |
| Count | «ثَلَاثَةُ أُمُورٍ …» (only when the text itself counts) | ثَلَاثٌ لَا يُغْفَرْن |
| Direct address | «أَنْتَ مَأْمُورٌ بِـ…» | أَنْتَ مَأْمُورٌ أَنْ تَكُونَ مَعَ أُنَاسٍ بِأَعْيَانِهِم |

For a long-text reel the hook is still short: it asks the question the prose block will answer.

Rejected formulas (clash with the brand): «nobody tells you this», «stop doing X», shock numbers,
countdown bait, anything that implies the audience is ignorant.

## A/B variants

Produce a second hook when asked (or when the first is a plain question): change only scene 1's text
(keep the length), re-run build/mix/verify, and publish 3–4 days apart or as Trial Reels. Judge by
average watch time and sends-per-reach (`references/platforms.md`), never by likes.

## What does not change in v3

- The image system (paper, green, gold; Amiri/Kufi/Naskh) — `references/brand.md`.
- The three layers — نصّ / شرح / استنباط — `references/brand-voice.md`.
- No narrator, no cover, no clickbait; the reel works muted.
- One hero per reel, one idea per reel, one reference per claim.
