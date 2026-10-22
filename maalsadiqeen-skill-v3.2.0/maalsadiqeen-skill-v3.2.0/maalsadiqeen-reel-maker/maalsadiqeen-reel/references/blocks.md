# Spec format & block library (`scripts/build_reel.py`)

A reel is a JSON spec: metadata + `audio` + an ordered list of `scenes`. Each scene is one **block**.
`build_reel.py spec.json --out <project>` compiles it to a HyperFrames project and writes
`spec.resolved.json` with every cue in absolute seconds (consumed by `mix.py` and `verify.py`).

```json
{
  "id": "slug", "title": "…", "duration": 45,
  "life_impact": "one concrete change in the viewer's week",
  "brand": { "handle": "maalsadiqeen" },
  "watermark": { "show": true },               // optional: "from"/"until" seconds
  "audio": { … see audio.md … },
  "scenes": [ { "id": "s1", "type": "hook", "start": 0, "end": 3.4, … }, … ]
}
```

Rules enforced/derived by the builder:

- Scenes are contiguous (`end` of one = `start` of the next; `end` may be omitted). Last `end` = `duration`.
- `cues` are optional. Omitted cues come from reading-speed defaults (see §2). Given cues may be
  absolute seconds or relative strings `"+1.2"` (from the scene start).
- Font sizes are fitted per block with exact Arabic shaping (Pillow + raqm), capped at brand ranges.
- `<em>…</em>` inside any text field = gold emphasis. Plain `<` and `&` are escaped automatically.
- A warning prints as `WARN …`. **`last reveal … less than 0.9 s before the scene ends` is never
  ignored**: the fix is to extend the scene, not to cut the sentence in half.

Two families of blocks. The short-form nine are one idea per screen; the long-text six carry a
passage. A reel is built from either family, or from both — the spine never changes.

| block | family | typical s | what it is for |
|---|---|---|---|
| `hook` | short | 3.0–4.5 | the first frame: one question, one turn |
| `verse` | short | 8–14 | an āyah, word by word, with recitation |
| `quote` | short | 8–12 | a ḥadīth or a scholar's sentence, with attribution |
| `contrast` | short | 6–9 | what it is *not* vs. what it is |
| `answer` | short | 7–9 | one hero line — the screenshot frame |
| `proof` | short | 7–10 | book · volume · page, and a seal only with a grading |
| `list` | short | 8–10 | ≤ 4 short items |
| `title` | short | 3–4.5 | an occasion, a name, a section card |
| `cta` | short | 6.4–7.4 | take-away + share + brand card |
| `paragraph` | long | 10–16 | a passage of prose, sentence by sentence |
| `definition` | long | 9–13 | what a word means — the term, then the حدّ |
| `steps` | long | 11–15 | an ordered practice, 2–4 steps |
| `timeline` | long | 12–16 | 2–4 moments in order |
| `compare` | long | 11–15 | two readings side by side, then the verdict |
| `qa` | long | 12–18 | a real question answered in full sentences |

---

## 1 · The stage

1080 × 1920, `#ece6da` paper, green `#1f4a35`, gold `#957238`. The stage is a centred flex column
with `padding: 0 130px 150px 150px`, so every block gets **800 × 1770 px** of usable canvas.

That number decides everything else: a Naskh line at 44 px holds ≈ 7–8 Arabic words in 800 px, and
eight such lines fill the canvas. **If the copy does not fit at 36 px, it is not a screen text.**

## 2 · Reading speed (the defaults)

| constant | value | used by |
|---|---|---|
| `READ_WORD` | 0.26 s / word | short-form lines (`hook`, `quote`, `list`, `title`, `contrast`, `proof`, `cta`) |
| `READ_MIN` | 1.15 s | the floor for a short line |
| `GAP` | 0.18 s | between two reveals |
| `READ_PROSE` | 0.30 s / word | `paragraph`, `definition`, `qa`, `compare`, `steps`, `timeline` |
| `PROSE_MIN` | 1.80 s | the floor for a prose sentence (2.1 s in `timeline`) |

A prose cue therefore lasts `max(1.80, 0.30 × words + 0.55) + 0.18` seconds. A 12-word sentence =
4.3 s. Five sentences = 21 s — which is why a long-text reel holds **one** dense block plus four
short ones, not five dense blocks.

## 3 · The word budget

`copy_lint.py` counts every word that appears on screen (sources and labels excluded).

- **soft** `max(95, 2.3 × duration)` — warn;
- **hard** `max(110, 2.9 × duration)` — fail.

At 40 s that is 95 / 116 words; at 53 s, 122 / 154. The prose blocks are what make 120 words
possible at all: the reader follows one sentence at a time instead of scanning eight lines.

---

## Short form

### hook — the first 3–4 s

| field | role |
|---|---|
| `lead` (+ `lead_font` quran\|amiri) | quoted fragment, 0.92 opacity, small |
| `line1` | kufi, e.g. «فَمَنْ هُمُ» |
| `line2` | the big word(s) with gold underline bar, kufi ≤ 138 px |
| `sub` | naskh, source line |
| `cues.emphasis` | underline + pulse (default `min(end−1.2, start+1.9)`) |

Order: lead +0, line1 +0.16, line2 +0.34, rule +0.85, sub +1.0. A hook longer than 4.5 s is a
warning; the first cut must land inside the 3-second cliff.

### verse — Qurʾanic text, word by word

`label` («﴿ سُورَةُ … — ١١٩ ﴾»), `lines` (list of word-lists, forced breaks between lists), `font`
(`quran` default | `amiri`), `size`, `nowrap`, `max_lines` (4), `highlight {words:[…], at}`
(1-based indices → gold + 1.05), `cues.words`. Words animate 0.28 s before their cue. The scene must
be ≥ recitation length + 1.6 s (+0.8 s with a label).

### contrast — strike the wrong reading, light the right one

`wrong_label`, `wrong` (struck), `right_label`, `right` (one `<em>`), `line3` (kufi), `line4`
(naskh; its `<em>` turns gold later). Cues: `wrong`, `strike`, `right`, `line3`, `line4`, `line4_gold`.

### answer — the hero moment

`q1` (amiri), `q2` (naskh, ends with «:»), `hero` (amiri bold ≤ 118 px: wipe + gold underline + glow
+ 1.028 push), `after` (amiri), `source` (naskh). One hero per reel; place it at 50–65 % of runtime.

### proof — authority

`seal` (`["صَحِيحُ","السَّنَد"]`, or omit), `cards` (≤ 3 × `{book, loc, grade}`), `line1`/`line2`
(amiri bold; line2 gold), `attribution`. A seal without a stated grading is a `copy_lint` failure.

### cta — take-away + one invitation (or none) + brand

`line1` (kufi + drawn gold path), `line2` (amiri + `<em>`), `final` (+ `final_font`, gold rule),
`brand.handle`, and **optionally** `share` + `icon`.

- `share` is empty by default. Fill it with **one** ending from `config/brand.json → cta.endings`, or
  leave it empty: a heavy or sensitive reel ends with the verse and the card, and that is complete.
- `icon` is `send` (paper plane), `save` (bookmark) or `none`. It follows the verb: «أرسل» → plane,
  «احفظ» → bookmark. Omitted, it is read from `cta.icons`, then from the verb.
- Two invitations in one ending is a `copy_lint` failure (أرسل + احفظ, or «اشترك» anywhere).
- «أَرْسِلْهَا لِمَنْ تُحِبّ» and its family are **forbidden** — `copy_lint` fails them.

Minimum 6.4 s; with no invitation the closing line takes the middle of the screen (`.no-invite`) and the
brand card still needs 1.5 s alone.

### quote — a ḥadīth or a scholar's sentence

`label`, `text` (string or list of lines), `reveal: "lines"|"words"`, `font` (amiri), `hero: true`
(underline + glow + push), `attribution`, `size`, `max_lines`.

### list — ≤ 4 short items

`title` (kufi), `items` (naskh, Arabic-Indic numbering unless `numbered: false`), `attribution`.

### title — occasion / section card

`kicker` (kufi-r gold), `title` (kufi ≤ 110 px + gold rule), `sub` (naskh).

---

## Long form (v3)

The six long blocks exist for the text that arrives as 700–1800 words and still has to become one
calm reel. They share three promises:

1. **One sentence per reveal.** Nothing appears as a wall; the eye is always told where to start.
2. **Book typography.** Body copy is right-aligned Naskh with a gold margin rule — the page metaphor
   of the brand, not a slide of bullets.
3. **A ceiling.** 60 words in a `paragraph`, 3 points per column in `compare`, 4 items in `steps` and
   `timeline`. Beyond that it is a carousel or a series, not a reel.

### paragraph — a passage of prose

| field | default | notes |
|---|---|---|
| `kicker` | — | small gold label («فِي اللُّغَة», «الشَّرْح») |
| `text` | required | a string (split at `. ؟ !`) or a list (one entry per reveal) |
| `source` | — | naskh, bottom, ink-2 |
| `font` | `naskh` | `amiri` for a quotation |
| `size` | fitted 56→36 | px |
| `max_lines` | 8 | the fit gives up on size before giving up on lines |
| `max_words` | 18 | a longer sentence is split at its last «،» before that limit |

Cues: `kicker`, `p1…pN`, `source`. A sentence carrying `<em>` is never split. More than 7 sentences
warns — that is two paragraphs.

**Budget the scene**: `1.2 s + Σ max(1.80, 0.30w + 0.55) + 0.18 per sentence + 1.2 s`.
A 34-word passage in three sentences needs ≈ 13.8 s. Measured example:
`assets/examples/long-text-sadiq.silent.json` scene 2.

### definition — حدّ المصطلح

`label` (default «التَّعْرِيف»), `term` (Kufi ≤ 104 px, gold rule under it), `body` (prose, 1–3
sentences), `note` (small, ink-2), `source`. Cues: `label`, `term`, `p1…`, `note`, `source`.

Use it when the whole reel turns on one word — and only one word. Two definitions in one reel means
the idea is still two ideas.

**Budget**: `0.3 + 0.9 (label) + 1.2 (term) + Σ body + 0.9 (note) + 0.9 (source) + 1.0`.
Nine to thirteen seconds.

### steps — خطوات مرقّمة

`title`, `items` (2–4 × string or `{head, text}`), `source`. The rail and the Arabic-Indic numerals
carry the order; `head` is «أَوَّلًا» at most, never a second sentence. Cues: `title`, `i1…iN`,
`source`. Each step is `max(2.0, 0.32 × words + 0.55)` seconds — a step is an action, not a
paragraph.

**Budget**: `0.3 + 1.2 + Σ steps + 1.1 + 1.0`. Three steps of ten words ≈ 13 s.

### timeline — خطّ زمني

`title`, `events` (2–4 × `{when, text}`), `source`. `when` is written for the ear — «سَنَة ١٤٨ هـ»,
«بَعْدَ وَفَاتِهِ», «اليَوْم» — never an ISO date, never ASCII digits. Cues: `title`, `e1…eN`,
`source`; the first reveal lands 0.3 s in, each event `max(2.1, 0.32 × words + 0.55)`.

**Budget**: `0.3 + 1.2 + Σ events + 1.1 + 1.0`. Four events ≈ 15 s — this is the anchor scene of a
`J` reel, not a decoration.

### compare — مقارنة هادئة

```json
"col_a": { "head": "الظَّنُّ الشَّائِع", "points": ["…", "…"] },
"col_b": { "head": "النَّصُّ",             "points": ["…", "…"] },
"verdict": "…", "source": "…"
```

Two columns, a hairline between them, a diamond bullet per point, at most three points each and
eight words per point. **The columns are revealed in pairs** (both heads, then a1 with b1, a2 with
b2, then the verdict) because a comparison is read across, not down. `col_a` is the common
assumption, `col_b` is what the text says; never caricature a named group in `col_a`.

**Budget**: `0.3 + 1.2 (title) + 2.1 (heads) + Σ max(2.0, 0.32 × longest pair + 1.35) + verdict + 1.2`.
Two points a side ≈ 13 s.

### qa — a question answered in full

`label_q` («السُّؤَال»), `question` (Kufi ≤ 64 px), `label_a` («الجَوَاب»), `answer` (prose, 2–5
sentences), `note`, `source`. Cues: `label_q`, `q`, `label_a`, `p1…`, `note`, `source`, plus `hero`
(the first answer sentence — `mix.py` puts the soft impact there).

`answer` (short block) is **one line**; `qa` is **the long form**. If the answer is a sentence, use
`answer`; if it is a paragraph, use `qa`. `note` is where «وَمِنْ ذَلِكَ…» goes — the extension, never
a second answer.

**Budget**: `0.3 + 0.9 + 1.2 + 1.4 + Σ answer + 1.1 (note) + 1.1 (source) + 1.0`. Three sentences of
ten words ≈ 15.5 s.

---

## Choosing a block

| the text gives you | block |
|---|---|
| a question the viewer already asks | `hook` |
| an āyah | `verse` |
| a ḥadīth or a scholar's sentence | `quote` |
| a misreading to correct | `contrast` |
| one decisive line | `answer` |
| a chain, a grading, a page | `proof` |
| three consequences | `list` steps / `steps` if ordered |
| a date, a person, an occasion | `title` / `timeline` |
| a definition | `definition` |
| a paragraph of explanation | `paragraph` |
| two positions | `compare` |
| a real question with a real answer | `qa` |

## Layout limits (so nothing overflows the 800 × 1770 stage)

| block | fits at | ceiling |
|---|---|---|
| `paragraph` | 56 px for ≤ 2 sentences, 44–48 px for 3–4 | 8 rendered lines, 60 words |
| `definition` | term 104 px, body 48 px | body 3 sentences, note one line |
| `steps` | head 46 px, text 40 px | 4 steps × 3 lines |
| `timeline` | when 38 px, text 40 px | 4 events × 3 lines |
| `compare` | head 46 px, point 36 px | 2 columns × 3 points × 3 lines |
| `qa` | question 64 px, answer 46 px | 5 sentences, note one line |

The builder fits down to 36 px and then stops. If a warning says the fit hit the floor, the copy is
too long — cut it; never hand-set a smaller size.

## Timing recipes

- `verse`: recitation + 1.6 s (+0.8 s with a label).
- `answer`: hero at ≈ start + 3.0 s; scene ≥ 8 s so the hero holds ≥ 4 s.
- `proof`: 1 card 7.5 s · 2 cards 9 s · 3 cards 10.5 s.
- `cta`: 6.4 s minimum; 7.4 s when `final` is a full āyah.
- `paragraph` / `definition` / `qa` / `steps` / `timeline` / `compare`: **do not guess the length.**
  Run `python3 scripts/retime.py spec.json --write` after writing the copy: it measures every block
  with the builder's own cue model, sets the scene to `last cue + 1.0 s` and shifts what follows
  (short-form scenes keep their length; the `cta` is only ever grown). Then build and read the
  output. A `last reveal … 0.9 s` warning that survives `retime.py` means the copy is longer than one
  screen — cut a sentence, never squeeze the timing. `verify.py`'s «longest static stretch» is the
  other half of the same rule: a block that outlives its words.

## Extending the library

Add `blk_<name>(sc, ctx)` in `build_reel.py`: append HTML to `ctx.html`, GSAP calls to `ctx.js`, cues
to `ctx.cues[sid]`, and register it in `BLOCKS` (and in `LONG_TEXT_BLOCKS` if it is prose). Reuse
`_seq_texts` for prose pacing, `enter/exit/heroIn/drawPath` for motion; keep CSS class-scoped under
`.blk-<name>`; never animate `#root` and never set `dir` on `<html>` (it renders a blank video).

Then, in the same commit: `copy_lint.fields_of` + `BUDGET`, `mix.auto_events`, `verify.key_times`,
`scenarios.BLOCK_TYPES` + `scene_summary`, `social_kit.scene_text`, `post_kit`, `beat_sheet.TEXT_KEYS`,
`preview_frames.frames_for`, and an example spec under `assets/examples/`. A block that only renders
is half a block.
