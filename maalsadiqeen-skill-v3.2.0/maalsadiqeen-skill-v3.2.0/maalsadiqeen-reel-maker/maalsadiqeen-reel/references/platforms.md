# Platforms — one reel, three captions

The video is the same everywhere; the *text around it* is not. Posting the Instagram caption on
Facebook reads as an advert, and the X version must lose two thirds of it. `captions.py` composes and
validates all three; this file explains the judgement behind the numbers in `config/brand.json`.

## 1 · The short version

| | **Instagram** (primary) | **Facebook** (secondary) | **X** (tertiary) |
|---|---|---|---|
| job | discovery + saves | discussion + shares to family | a quotable line for the already-convinced |
| length | 600–1200 chars (hard 2200) | 400–900 chars (hard ~63 k) | **180–250, hard 250** |
| first line | ≤ 125 chars (the fold) | ≤ 200 chars | ≤ 60 chars |
| hashtags | 3–5 | 0–2 | 0–1 |
| link in body | never | never (first comment) | never (reply) |
| question | optional, at the end | required | optional |
| emoji | no | no | no |
| what it punishes | walls of text above the fold, bait | off-platform links, no conversation | long posts, hashtag stuffing |
| metric that matters | watch time, sends/reach, saves/reach | 3-second views, shares, comments | replies, reposts, profile clicks |
| window (Baghdad) | 19:00–22:30, Thu–Sat | 20:00–23:00, Thu–Fri | 21:00–23:00, Fri–Sat |

## 2 · Instagram — the primary surface

Instagram is where the page grows, so the caption is written first for it.

Structure:

```
<line 1: the hook, ≤ 125 chars — it must survive the fold>
<blank>
﴿the verse﴾ — sūrah + āyah            ← layer 1: نصّ
<blank>
المصدر: الكتاب جX صY + the grading      ← source etiquette
<blank>
the meaning in 2–3 sentences            ← layer 2: شرح (named if a scholar)
<blank>
الأثر في الحياة:
<one deed>
<blank>
<one question to the reader>
<blank>
أَرْسِلْهَا لِمَنْ تُحِبّ · احْفَظْهَا لِلْعَوْدَةِ
<blank>
#مع_الصادقين #معارف_أهل_البيت #<one topic> #<one imam>
```

Rules:

- The hook is the **first 125 characters**; do not waste them on «بسم الله» or a greeting.
- No link, ever, in the body: «الرابط في البايو». A link costs reach.
- 3–5 hashtags, chosen by topic + imam, not by volume. No generic `#اسلام` or `#قرآن` unless the
  topic map says so.
- The save is the goal: give a reference a reader will want to come back to.
- Alt text is written for a blind reader, not for keywords.

Reels specifics: first frame decides; sound optional but a recitation helps; 30–50 s; post as a
Reel, not a feed video. Trial Reels (shown to non-followers first) are the right place to test a new
hook (see `instagram-growth`, vendored).

## 3 · Facebook — the discussion surface

Facebook readers are older, read more, and share to family groups. The caption is an argument, not
a teaser.

Structure:

```
<the claim, one sentence>
<blank>
the meaning + the source in the same paragraph
<blank>
the distinction that makes it worth reading
<blank>
الأثر في الحياة:
<one deed>
<blank>
<one real question>
<blank>
#مع_الصادقين (0–2 tags)
```

Rules:

- No links in the body; put the link in the first comment if there must be one.
- A question is required — Facebook rewards comments, not impressions.
- 0–2 hashtags; more looks like spam to this audience.
- Write the meaning in full sentences; do not rely on the video being watched.

## 4 · X — the quotable surface

X is not a place to explain; it is a place to say one true thing well.

Structure (all within 250 characters):

```
<one complete claim, ≤ 60 chars>
<blank>
﴿the shortest sufficient part of the verse﴾
— <the meaning in one line, optional>
<book, volume, page>
```

Rules:

- The hard limit is 250 characters — the skill refuses longer posts. A thread is allowed but each
  post is written as its own complete sentence.
- 0–1 hashtag. Choose none unless the post is part of a campaign.
- No link in the post; reply with it if necessary.
- No «🧵» or thread markers; the thread reads as continuous prose.

## 5 · Hashtags

| set | examples | rule |
|---|---|---|
| core (always) | `#مع_الصادقين` `#معارف_أهل_البيت` | both on Instagram; one on Facebook; none needed on X |
| topic (one) | `#رجال_الحديث` `#الولاية` `#تفسير_القرآن` `#فقه_أهل_البيت` `#الأخلاق_الإسلامية` | chosen by the subject, from the map in `config/brand.json` |
| imam (one) | `#الإمام_الرضا` `#الإمام_الصادق` `#أمير_المؤمنين` | only when the Imam is the subject |

No hashtag stuffing, no unrelated trending tags, no English tags.

## 6 · Cross-posting

Order: **Instagram → Facebook → X**, never simultaneous.

1. Instagram first: it is the primary surface and the file is native there.
2. Facebook 10–20 minutes later, with the rewritten caption and the question.
3. X last, with the compressed version. Quote-post the Instagram link only if it adds something.

Never paste the same text in two places: the platforms notice, and the reader who follows you on
both notices more.

## 7 · What the scripts check

`captions.py` fails a caption that breaks a hard limit (length, hashtags, link, emoji, exclamation,
Latin text, missing reference, follow-bait CTA) and warns on the soft ones (outside the target band,
first line over the fold, no question on Facebook). A **reference** is a work named in full (الكافي،
نهج البلاغة، لسان العرب، مجمع البيان …), a locator (`ج٢ ص١٠٤`، `مادة: صدق`، `الخطبة ١٠٤`، `حديث ٣`),
or both — tashkeel is ignored when matching, so a vocalised source still counts.
`social_kit.py` aggregates the three verdicts into `validation.md`; `verify.py --kit` reads it.

## 8 · Timing

Windows in `config/brand.json → posting_windows`. They are starting points, not laws:

- publish inside the window when the audience is in the Gulf/Iraq;
- keep 3 reels a week, at least 3 days apart for an A/B pair;
- read the first 60 minutes (comments answered, pinned source) and the 48-hour review in `publish.md`;
- judge on watch time and sends, never on likes.
