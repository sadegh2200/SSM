# Publishing playbook (Instagram Reels first; TikTok/YouTube Shorts reuse the same master)

Distilled from the ig-reel / viral-instagram-reels skills, filtered for a scholarly page. Applies to both
engines (HyperFrames default, Remotion studio alternate).

> **v3:** the publishing kit is produced by `scripts/social_kit.py` (captions for IG/FB/X, the seven-comment
> bank, the schedule and the validation report) — see `references/platforms.md` and
> `references/comments.md`. `post_kit.py` still writes the single-file `post.md` for the legacy flow, but
> the platform rules it predates have moved on: prefer `social_kit.py`.

## Deliverables per reel (`export_variants.py`)

- `<name>.mp4` — 9:16 master (1080×1920, 30 fps, −15.5 LUFS).
- `<name>-cover.jpg` — **optional, only with `--cover`**: frame at hero + 0.9 s. By default no cover is
  exported; Instagram uses the first frame, and `verify.py` already checks that it is readable.
- `<name>-feed-4x5.mp4` — for the grid if the account posts reels to the feed with a 4:5 preview.
- `beat-sheet.md` — scene table with cues, copy, sources (the user re-uses it for the caption and for
  translators).
- `caption.txt` / `post.md` — 3–5 lines + 3–5 keywords (arabic-copy.md), pinned comment with every reference
  and grading that is on screen (`post_kit.py`).

## What the algorithm rewards (and how this format answers it)

| signal | design answer |
|---|---|
| 3-second cliff / average watch time | hook word on screen by 1.2 s; first cut ≤ 4.5 s; no static frame > 3.4 s |
| completion | 36–50 s; the hero at 50–65 %; the final line + brand at the end rewards staying |
| sends per reach (the strongest 2025–26 signal) | explicit «أَرْسِلْهَا لِمَنْ تُحِبّ»; a screenshot-able hero frame |
| saves | the proof scene (references) makes it a note worth keeping; caption repeats the reference |
| originality / 30-day rule | never re-upload the same cut; A/B hooks count as different reels; use Trial Reels for tests |
| sound-off viewing | text-led design; recitation is a bonus, never required to understand |

## Posting routine

1. Upload the master, pick `<name>-cover.jpg`, write the caption with the reference in line 1–2.
2. Keywords in the caption as searchable words, 3–5 hashtags max (`#مع_الصادقين` + topic + Imam's name).
3. Trial Reels (accounts > 1K followers) to test a second hook with non-followers; promote the winner.
4. Post 3–4 days apart when comparing variants; same time-of-day; compare **average watch time**,
   **sends/reach**, **saves/reach**, then follows/reach. Views alone decide nothing.
5. Reply to the first comments with the full reference text; pin the best question.
6. Reuse: the 4:5 crop for the feed a week later; the hero frame as a static sheet for stories.

## Series logic

Give reels a recurring label the audience can recognise («سؤال وجواب», «كلمة واحدة», «من هم؟»); keep
the opening 0.3 s (paper + arc draw) identical across the series — it becomes the brand's audio-visual
signature.

## Diagnosing a flop (after 48 h)

- Low average watch time (< 40 %): hook problem → re-cut scene 1 only (A/B).
- Good watch time, low sends: the take-away line is not quotable → rewrite `cta.final`/hero.
- Good sends, low follows: brand card too short or the handle not readable → ≥ 1.5 s, check cover.
- Comments arguing the reference: add a second proof card next time or quote the grading verbatim.

## Anti-patterns for this niche (hurt distribution *and* dignity)

- Rhythmic/pop music under sacred text (comments turn hostile; sends drop) — the bed is a non-rhythmic pad/drone.
- Faces, AI "cinematic" scenes of holy figures, flashing red warnings, stock footage.
- More than one ḥadīth per reel, > 10 quoted lines, > 5 points, > 60 s.
- Begging CTAs («تابعونا», «لايك»), emoji, exclamation stacks, Latin words, dialect.
- Reusing another page's footage or screenshots (originality is a ranking signal; reposters lose reach).

## Cold-start checklist (first 60 minutes)

- Post 19:00–22:00 Baghdad/Riyadh; Thursday–Friday nights peak for religious content.
- Pin the references comment (`post.md`); answer the first 10 comments with substance (a source, a page number).
- Share to Story with an «أرسِل لمن…» sticker; ask 3–5 trusted accounts to *send* (not like) the reel.
- After 24 h read retention: early drop → re-cut scene 1 only (A/B hook); drop in the middle → shorten that
  scene in the spec (or `plan.py --target 40` on the Remotion engine); high completion but low sends →
  a recipient-naming CTA («أرسِلْها لِـ … حتى …»).
