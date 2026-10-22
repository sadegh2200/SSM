---
name: maalsadiqeen-reel
description: Use when the user wants a reel / short vertical video (ریل، ویدیو، ریلز، reel, Reels) for «مع الصادقين» (@maalsadiqeen), or hands over any Arabic religious text — a page of a book, a lecture transcript, a forwarded message, a question, a long article — or the page's branded sheets (ورق، پست، پوستر — cream paper, green arc, tree logo) carrying a verse, ḥadīth, sanad grading, scholar quote, question or occasion, and wants it turned into a 30–60 s faceless reel. Triggers on «این متن را ریل کن», «از این ورق ریل بساز», "same style as the Ṣādiqīn reel", and even when the user only asks for a scenario, a hook, a caption, the three-platform copy, a comment bank, or a QC of an existing cut.
license: Proprietary — made for the maalsadiqeen page; third-party assets per assets/sfx/CREDITS.md and font licences (OFL).
metadata:
  title: Maalsadiqeen Reel Maker — ریل‌ساز مع الصادقین
  version: 3.2.0
  brand: maalsadiqeen
  output: 1080x1920 MP4 (30 fps, ≤60 s) + IG/FB/X captions + 7-comment bank + schedule (cover only on request)
  requires: python3 ≥3.9 (numpy, pillow), ffmpeg (ffprobe optional), node ≥22 + hyperframes 0.8.x for the render — or node + remotion 4 (alternate engine)
---

# Maalsadiqeen Reel Maker (`maalsadiqeen-reel`) — from any text to a finished reel

You are not converting a poster into a video any more. You are turning **any text** into a small,
calm, sourced piece of knowledge: read it, write a brief, offer **four scenarios**, let the user
choose, then build **one** reel and hand over its publishing kit.

The whole skill is three ideas:

1. **Text-first.** The input can be anything — a chapter, a transcript, a screenshot, a question. The
   contract for reading it is `references/text-intake.md`.
2. **A gate before the build.** Four complete, scored scenarios; the user picks; nothing is rendered
   before that. `references/scenarios.md`.
3. **A machine-checked voice.** The brand's wording rules are enforced by scripts, not by memory:
   `copy_lint.py`, `captions.py`, `comments.py`, `social_kit.py`, all against `config/brand.json`.

## Non-negotiables

1. **No human or synthetic narrator** unless the user asks in this conversation. Recitation is
   welcome when a verse is on screen. The reel must make sense muted.
2. **9:16 1080×1920, 30 fps, ≤ 60 s.** Default **40 s** (30–50 window). There is no 90-second version.
3. **Brand = paper, green, gold** (`references/brand.md`) **and the voice in
   `references/brand-voice.md`**: scholarly, calm, classical Arabic, never clickbait, never dialect,
   no emoji, no exclamation marks. The reader is `references/audience.md`.
4. **Three layers, always legible:** نصّ (verbatim + reference) · شرح (named scholar) · استنباط
   (ours, marked). Never dressed as one another.
5. **No invented reference or grading.** No source → no proof block; say so in the summary.
6. **No building before the user chooses a scenario.** `reel.py build --choose …` is the only door.
7. **Gates are green before delivery:** `copy_lint` 0 failures, three captions valid, seven comments
   valid, `verify.py` 0 failures. A red `validation.md` is not shipped.
8. **Reply in Persian; on-screen copy in Arabic.** No cover image unless the user asks (`--cover`).
9. **Density is budgeted, not decorated.** A long text is not solved by putting more on screen: one
   `paragraph` / `definition` / `qa` / `steps` / `timeline` / `compare` is the anchor, the others stay
   short, and the whole reel stays inside ~2.3 words per second (hard 2.9). If a paragraph and a
   definition say the same thing, one of them is cut.
10. **The ending asks for one thing — usually nothing.** At most one invitation, and only when the
    text earns it: a save for a definition or a reference, a send to the person who asked, and **no
    invitation at all** for an occasion, a life, an objection or a ruling. «أَرْسِلْهَا لِمَنْ تُحِبّ»
    is forbidden — `copy_lint` fails it. The brand card closes the reel in silence.

## v3 in one picture

```
text / sheets / question
        │  intake.py            normalise · quotes · references · shape
        ▼
   brief.md  (one idea, layers, life-impact)
        │  scenarios.py         4 scenarios · 8 angles · scored
        ▼
   scenarios.md + preview/     ──►  ⛔ THE GATE: user picks «۲» or «۲ و ۴»
        │  reel.py build --choose
        ▼
   spec.json → project → mix → verify → [render] → kit
        │
        ▼
   MP4 · captions/ (IG·FB·X) · comments.md · publish.md · validation.md
```

## Workflow

Paths come from `scripts/env.sh`: `$SKILL_DIR`, `$REEL_WORK` (default `./reel-work`),
`$REEL_DELIVER` (default `./reel-deliver`), `$HF_WORKDIR`. Override before sourcing.

### 0 · Toolchain

```bash
bash <skill>/scripts/bootstrap.sh --check     # what is missing, nothing is installed
bash <skill>/scripts/bootstrap.sh            # install (pip --user, npm in $HF_WORKDIR)
source <skill>/scripts/env.sh
S="$SKILL_DIR/scripts"; W="$REEL_WORK/<slug>"; D="$REEL_DELIVER"
```

`ffprobe` is optional since v3: `_common.media_duration()` falls back to `ffmpeg -i`. A render still
needs node ≥ 22 + hyperframes. **Missing toolchain never blocks the plan, the captions or the kit** —
only the render (see “degrade honestly”).

### 1 · Intake — any text into a brief (`references/text-intake.md`)

```bash
python3 $S/reel.py intake <file|dir|-> --slug <slug>      # text, a folder, or stdin
python3 $S/reel.py intake --slug <slug> --sheets a.jpg b.jpg   # sheets/images too
```

`intake.py` writes `input.txt`, `brief.seed.json`, `brief.seed.md` (Persian) and flags:
a ḥadīth with no source, a quote with no reference, unreadable words, a text that needs a series.
Then **you** write `brief.md` in Persian using the template in `text-intake.md` §7 — one idea, the
three layers, the life-impact, the shape. Ask at most **three** questions, in one message.

### 2 · Plan — four scenarios, then stop (`references/scenarios.md`)

```bash
python3 $S/reel.py plan <slug>                 # scaffolds scenarios.json with 4 angles
# fill every «…» — hooks, scenes, sources, life_impact, why_fa
python3 $S/reel.py plan <slug> --finalize      # validate + score + scenarios.md + preview → GATE
```

`plan` reads the intake: a text over ~700 words (or one the intake wants to split) is scaffolded from
G–L, everything shorter from A–F. Change the pattern if the material asks for it, and say why in
`why_fa`. For a long-text scenario, replace the prose blocks with real sentences and budget them with
the formulas in `blocks.md` §Long form — a `«…»` left in a `paragraph` fails `copy_lint`.

Present the table (angle, promise, duration, cost, score), open `preview.html`, and ask which
one. **Do not build.** If the user says «همه», build them as separate deliveries, one at a time.

### 3 · Build — one scenario (`references/narrative.md`, `blocks.md`)

```bash
python3 $S/reel.py build <slug> --choose 2 [--preset minimal|standard|full] [--render]
```

This runs, in order: compile `spec-2.json` → `copy_lint` (aborts on failures) → `build_reel.py`
(`project-2/`) → `mix.py` → `verify.py --light --source-spec` → `social_kit.py` into
`$REEL_DELIVER/<slug>-2/kit`. With `--render` and a working toolchain it also renders and re-verifies.

If a verse is on screen, fetch the recitation **before** the build and size the verse scene from it:

```bash
python3 $S/recite.py 9:119 --out $W/recite.wav
python3 $S/cues.py $W/recite.wav --words 8 --offset <verse start> --json
```

Fix `spec.json` and re-run; never hand-edit the generated `index.html`. If `copy_lint` reports a
tashkeel, spelling or register problem and the fix is not obvious, open `arabic-editor`; if it reports
a seal or a reference, open `hadith-sanad`.

### 4 · Kit — the publishing half (`platforms.md`, `comments.md`)

Already produced by `build`; regenerate alone with:

```bash
python3 $S/reel.py kit <slug> --id 2 --preset standard
```

It writes `captions/{instagram,facebook,x}.txt`, `captions.json`, `alt-text.txt`, `comments.md`
(seven slots, scheduled in Baghdad time + UTC), `publish.md` (windows, cross-post order, first-hour
checklist, 48-hour review) and `validation.md`. Write better prose if you like, then validate it:

```bash
python3 $S/captions.py $W/spec-2.json --out $D/<slug>-2/kit/captions --texts captions.json
```

A caption that breaks a limit is written to `captions/_FAILED/` and the command exits 1.

### 5 · Render (3.5–6 min, one at a time)

```bash
bash $S/render.sh $W/project-2 $D/<slug>-2.mp4
python3 $S/verify.py $W/project-2 --render $D/<slug>-2.mp4 --no-check
```

### 6 · Deliver

```bash
python3 $S/export_variants.py $D/<slug>-2.mp4 --out $D --name <slug>-2 \
    --spec $W/spec-2.json --srt --alt-text [--cover] [--feed] [--square] [--audio]
python3 $S/beat_sheet.py $W/project-2 --spec $W/spec-2.json --out $D/<slug>-2-beat-sheet.md --lang fa
```

Present the MP4 and the kit. In the Persian summary: the idea and the angle the user chose, the scene
table, what was verified, the posting time and the first-hour checklist, and every uncertainty
(missing reference, unverified ḥadīth, unreadable word).

## Decision points

| situation | do |
|---|---|
| text with a verse **and** a ḥadīth | archetype A; recitation `ar.mahermuaiqly`; verse scene ≥ recitation + 1.6 s |
| ḥadīth with a reference, no verse | B; `quote` with `reveal: words`; proof cards without a seal unless a grading is stated |
| a concept / a scholar's point | C; the contrast block carries the turn |
| a question from a follower | D; answer as `list` (≤3) or `quote`; answer scene ≥ 8 s |
| a date, a person, an occasion | E; `title` card first; final = greeting line |
| an objection or a claim | F; state it fairly, answer from the text, never name a group |
| text longer than ~1800 words | series (`references/series.md`); one reel per idea |
| 700–1800 words, one idea | one reel from **G–L** (`narrative.md`); one dense block carries the prose |
| the reel turns on a word | H/G with `definition`; the term is the only display line |
| the text gives conditions or acts | I with `steps`; heads are «أَوَّلًا/ثَانِيًا», not sentences |
| a life, a chain, a history | J with `timeline`; dates written for the ear, Arabic-Indic digits |
| two readings, then a verdict | K with `compare`; the verdict is the text's, not ours |
| a follower's long question | L with `qa`; answer in sentences, then prove it |
| only one idea but a long text | one reel; the caption carries what the screen cannot |
| user asks for a cover | `--cover` (never by default) |
| user asks for > 60 s | decline; propose a two-part series with the same opening |
| user asks for narration | narrated mode: stems + `tighten.py` + `cues.py --lines`; target −14 LUFS |
| user asks for an A/B | `scenarios.py variant … --hook …`; change scene 1 only |
| toolchain missing | still deliver brief + scenarios + spec + kit, and print the exact commands that remain |

## Two palettes, one voice

`config/brand.json → themes` holds **main** (`النهار`, cream paper — the default) and **mourning**
(`ليلُ العزاء`, warm charcoal `#0e0f0e`, ivory text, muted gold, inverted logo). They are the same
layout, type and motion; only the tokens change.

```bash
python3 scripts/reel.py build <slug> --choose 2 --theme mourning   # a Muharram / Ṣafar reel
python3 scripts/build_reel.py spec.json --out "$REEL_WORK/x" --theme mourning   # or per build
```

`spec.theme` (set by `scenarios.compile_spec` from the brand default) is the third way. `verify.py`
prints the palette and its contrast. For the dark palette: no red, no pure black, no pure white — see
`references/brand.md` § «Two palettes». A mourning reel does not change its *voice*: the same calm
scholarly register, the same sources, and — per rule 10 — no invitation.

## Long text, one screen

When the input is 700–1800 words and one idea, the reel is still 30–60 s. The prose blocks are how the
argument fits:

| need | block | ceiling |
|---|---|---|
| a passage of explanation | `paragraph` | 3–4 sentences, ≤ 60 words |
| what a word means | `definition` | term + 3 sentences + one note |
| conditions, an ordered practice | `steps` | 4 steps × 12 words |
| a life, a chain, a history | `timeline` | 4 events |
| two readings, then the verdict | `compare` | 2 × 3 points |
| a real question answered in full | `qa` | 5 sentences |

Rules that keep it watchable: one sentence per reveal; every prose block right-aligned Naskh with a
gold margin rule (no bullets on prose); a scene is budgeted as
`0.30 × words + 0.55` per sentence, never shorter; and the rest of the reel returns to the short-form
blocks. Two prose blocks that both explain the same thing are one block too many — see
`references/blocks.md` §Long form for the exact formulas.

## The build reference

**Engines.** HyperFrames 0.8.x is the default and covers everything. Remotion studio is the alternate
for animated sanad chains and long rijāl carousels (`references/remotion-studio.md`); the brand, copy,
hook scorer and LUFS target are shared. Never mix engines in one reel.

**Blocks** (`references/blocks.md`): fifteen blocks in two families. Short form — `hook`, `verse`,
`contrast`, `answer`, `proof`, `cta`, `quote`, `list`, `title`. Long text — `paragraph`, `definition`,
`steps`, `timeline`, `compare`, `qa`. The builder fits Arabic type, paces short lines at ≥ 1.15 s +
0.26 s/word and prose at ≥ 1.80 s + 0.30 s/word, and writes `spec.resolved.json` with every cue.

**Sound** (`references/audio.md`): bed + recitation + automatic sound design derived from the cues;
no voice by default. Target −15.5 LUFS (narrated: −14). `mix.py --dry-run` prints the event list;
`--allow-missing-recitation` (used by `reel.py build`) keeps mixing when the recitation cannot be
fetched and says the result is **not publishable**.

**QC** (`references/qc.md`): `verify.py` checks spec/pacing, `index.html` sanity, hyperframes check,
snapshots, and (post-render) 1080×1920 · 30 fps · duration · AAC · LUFS · true peak. v3 flags:
`--light` (skip hyperframes + snapshots), `--no-audio` (no ffmpeg), `--source-spec` (run `copy_lint`
inside QC), `--kit` (read a kit's `validation.md`).

**Degrade honestly.** Without ffmpeg the build writes a silent placeholder and says so; without
node/hyperframes it stops before the render and prints the command. It never calls a placeholder a
master.

## The two in-house tools beside the pipeline

| skill | when | what it does |
|---|---|---|
| `arabic-editor` | before any copy goes on screen, and whenever `copy_lint` reports tashkeel, spelling or register | four passes — register, orthography, tashkeel, punctuation/line breaks — plus `ar_copycheck.py` |
| `hadith-sanad` | before a ḥadīth, a grading or a `proof` seal | records متن/سند/تخريج, validates the citation, and refuses a seal without a stated grading |

They are first-party (`skills/` in the repo root of this skill's parent), installed beside this skill
by `install-skill.sh`, and they never replace `copy_lint` — they explain what it found.

## Companion skills (installed beside this one)

Four third-party skills are vendored in `vendor/skills/` and installed in `.claude/skills/`,
`~/.claude/skills/` and `~/.agents/skills/`. **This skill is always the pipeline**; the companions are
reference material and tools.

| skill | use it for | guardrail |
|---|---|---|
| `skill-creator` | editing this skill, writing evals, validating frontmatter, packaging | not for producing reels |
| `ig-reel` | a second opinion on Reel structure, 26 hook formulas, beat-sheet math | English-first; score Arabic hooks with `scripts/hook_score_ar.py`, never its `hookscore.py` |
| `virat-design` | static frame / cover / carousel art direction when asked | its palette and Jakarta/Inter never override the paper/green/gold and Amiri/Kufi/Naskh |
| `instagram-growth` | reach/sends/watch-time diagnosis, eligibility, Trial Reels | WoopSocial references are inert; use native Insights; FB/X rules live in `references/platforms.md` |

Details, sources and rejected alternatives: `vendor/skills/README.md`.

## Files

| path | purpose |
|---|---|
| `config/brand.json` | handle, defaults, **themes (main · mourning)**, CTAs and their endings, hashtags, limits, windows, questions, comment slots, forbidden lists — the runtime source of truth |
| `config/content-log.json` | the last reels (diversity guard + learning loop); append, never delete |
| `scripts/reel.py` | front door: `intake` · `plan` · `build` · `kit` · `status` · `log` · `series` |
| `scripts/intake.py` | any text/sheets → `input.txt` + `brief.seed.{json,md}` + flags |
| `scripts/scenarios.py` | `init` · `validate` · `score` · `render` · `select` · `variant` · `compile` |
| `scripts/copy_lint.py` | on-screen verbal gate (placeholders, forbidden, dialect, tashkeel, seals, layers, budget) |
| `scripts/captions.py`, `scripts/comments.py`, `scripts/social_kit.py` | IG/FB/X captions + validation; seven-slot comment bank + schedule; the whole kit in one command |
| `scripts/preview_frames.py` | three frames per scenario (Pillow + raqm) or a self-contained `preview.html` |
| `scripts/bootstrap.sh`, `scripts/env.sh` | toolchain check/install; paths |
| `scripts/build_reel.py`, `scripts/mix.py`, `scripts/verify.py`, `scripts/render.sh` | spec → project; soundtrack; QC; render wrapper |
| `scripts/retime.py` | fits each long-text block to the copy it carries, then re-flows the reel (`--write`, `--target`) |
| `scripts/recite.py`, `scripts/cues.py` | recitation download/trim; word onsets |
| `scripts/hook_score_ar.py` | 7-dimension hook scorer (dignity included); `--profile classic` for the old weights |
| `scripts/export_variants.py`, `scripts/beat_sheet.py`, `scripts/post_kit.py` | SRT · alt text · optional cover/feed/square/audio; Persian beat sheet; legacy single-file post kit |
| `references/brand-voice.md`, `audience.md` | the verbal identity and the reader — read before writing any copy |
| `references/text-intake.md`, `scenarios.md`, `series.md` | input contract; the four-scenario gate; splitting a long text |
| `references/platforms.md`, `comments.md` | IG/FB/X rules and skeletons; the seven comment slots and moderation |
| `references/brand.md`, `content-analysis.md`, `arabic-copy.md`, `blocks.md`, `narrative.md`, `hooks-ar.md`, `audio.md`, `motion.md`, `qc.md`, `publish.md`, `troubleshooting.md` | visual tokens; reading the sheets; register and line budgets; the fifteen blocks and their timings; archetypes A–L; hook formulas; sound; motion; gates; posting; fixes |
| `../skills/arabic-editor`, `../skills/hadith-sanad` | the copy editor and the sanad discipline (installed as separate skills) |
| `references/remotion-studio.md`, `remotion-schema.md` | the alternate engine |
| `assets/templates/` | `scenarios.example.json` (one fully written scenario), `captions.example.json` (three valid captions) |
| `assets/examples/`, `assets/{fonts,brand,sfx,gsap.min.js,hyperframes.json}` | the gold-standard reels — `sadiqeen-9-119` (short form), `long-text-sadiq` (a 53.5 s G reel with `paragraph` + `definition` + `qa`) and `ashura-mourning` (the dark palette, an ending with no invitation) — and everything the builder copies into a project |
| `evals/` | self-contained test prompts, the rubric and the fixture texts |

## Done means

- The user chose the scenario; `scenarios.json` holds four valid, scored options.
- `copy_lint` 0 failures; `captions` 3/3 valid; `comments` 7/7 valid; `verify` 0 failures.
- The ending carries **at most one** invitation, and none of the forbidden formulas; a heavy text ends
  with the verse and the card. `verify.py` names the palette and its contrast.
- Every ḥadīth passed `hadith-sanad` (`sanad_check.py` 0 errors) and the copy passed `arabic-editor`
  (`ar_copycheck.py` 0 errors) — or the summary says exactly what is unresolved.
- The MP4 (1080×1920, ≤ 60 s, AAC, LUFS within ±1.2 of −15.5) plus `captions/`, `comments.md`,
  `publish.md`, `validation.md` sit in `$REEL_DELIVER/<slug>-<id>/`.
- Every quoted text matches the source; every reference is real; nothing was invented.
- The Persian summary says what was built, what was verified, what to check, and when to post.
