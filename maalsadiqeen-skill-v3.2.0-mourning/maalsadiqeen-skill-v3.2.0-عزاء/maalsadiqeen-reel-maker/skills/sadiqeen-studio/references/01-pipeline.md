# 1 · Recognition, treatment and the spec

Three stages, three contracts. The studio's job is to make each one *checkable*: a stage that
cannot be inspected is a stage that will be skipped.

## 1.1 Recognition — `director.py recognize`

Input can be anything the user pastes or points at. The recognizer never rewrites the text; it
extracts and it doubts.

| input | `kind` | what it does |
|---|---|---|
| `.md`, `.txt` | `text` | reads it whole |
| `.srt`, `.vtt` | `transcript` | drops indices and timecodes, keeps the words |
| a folder | `folder` | concatenates `.txt/.md/.srt/.vtt`, sorted |
| a reel `spec.json` | `spec` | passes it through (reels can be re-treated) |
| video/audio + sidecar `.srt` | `media+transcript` | reads the transcript |
| video/audio without `.srt` | `media-no-transcript` | **says so** — no transcription is invented |
| an image | `image-no-ocr` | **says so** — ask for the text, or for the page as text |

It answers, with evidence:

- **class A–F** — `A` verse + ḥadīth · `B` ḥadīth only · `C` concept/scholar · `D` question ·
  `E` occasion · `F` objection. Mixed input takes the class of its strongest single piece of
  evidence (a graded ḥadīth beats a paraphrase; a verse opens but cannot carry a reel alone).
- **the one idea** — the first sentence, as a seed; *you* rewrite it to ≤ 14 words in `brief.md`.
- **verses / references / grades / scholars / occasion** — regex extraction, `ج/ص` kept together
  («الكافي ج١ ص٢٠٨»).
- **confidence** — `0.18 + 0.16 × (how many of: verse, reference, grade, ḥadīth, scholar)`.
  Below 0.5 you are guessing, so you ask before you plan.
- **missing** — no reference → no proof block; a ḥadīth with no grade → no seal; a verse to verify.
- **questions** — at most three, all in one message, never a questionnaire.

## 1.2 Treatment — `director.py treat`

Three angles, not four, and never three wordings of one angle. Each carries: the angle, a hook
drawn from `hooks-ar.md` patterns, the block shape, a duration, five sub-scores and a total.

| class | the three angles |
|---|---|
| A | سؤال → جواب المعصوم · الكلمة التي تغيّر المعنى · المعنى في الحياة |
| B | كلمة واحدة تغيّر المعنى · موقف/قصة · تصحيح مفهوم |
| C | تصحيح مفهوم · المسألة ثم الحدّ · خطأ شائع ثم النصّ |
| D | سؤال → جواب · الجواب في ثلاث نقاط · السؤال كما يُسأل |
| E | مناسبة: عنوان ثم نصّ · المناسبة كسؤال · سطر واحد وبطاقة |
| F | الاعتراض كما يُقال ثم الجواب · تصحيح بمقارنة · النصّ وحده |

Scoring: clarity · evidence · tension · brand-fit minus risk. A treatment that needs a proof
block when the input has no reference is penalised — that is the risk term.

**The stop.** Show the table, say which one you would pick and why in one sentence, and wait.
«همه» means build them one at a time as separate deliveries.

## 1.3 The spec

The format is the brand skill's own (`assets/examples/*.silent.json`), so a reel written by
either skill can be built by the other.

```json
{
  "id": "slug", "title": "…", "duration": 45, "theme": "main",
  "life_impact": "one concrete change in the viewer's week",
  "brand": {"handle": "maalsadiqeen"},
  "watermark": {"show": true},
  "audio": {"target_lufs": -15.5, "recitation": {"ref": "9:119", "edition": "ar.mahermuaiqly"}},
  "scenes": [{"id": "s1", "type": "hook", "start": 0, "end": 3.4, "line1": "…", "line2": "…"}]
}
```

Rules the builder enforces or assumes:

- scenes are contiguous; the last `end` is the duration;
- `cues` are optional — omitted cues come from reading speed;
- `<em>…</em>` = gold emphasis inside any text field;
- `theme` is `main` or `mourning`; `--theme` on the command line wins;
- every field of every block is in §1.4; a field the block does not know is ignored, and that is
  a bug you should notice in the still.

### 1.4 Field reference

| block | fields |
|---|---|
| `hook` | `lead` (+`lead_font` amiri\|quran) · `line1` · `line2` · `sub` · `cues.emphasis` |
| `verse` | `label` · `lines` (list of word-lists; a list = a forced line break) · `font` quran\|amiri · `size` · `highlight {words:[1-based], at}` · `cues.words` |
| `quote` | `label` · `text` (string or list) · `hero` bool · `attribution` · `size` · `max_lines` |
| `contrast` | `wrong_label` · `wrong` · `right_label` · `right` · `line3` · `line4` · `cues.{wrong,strike,right,line3,line4,line4_gold}` |
| `answer` | `q1` · `q2` (ends with «:») · `hero` · `after` · `source` |
| `proof` | `seal` `[line1,line2]` (omit unless a grade is stated) · `cards` ≤3 × `{book, loc, grade}` · `line1` · `line2` · `attribution` |
| `list` | `title` · `items` ≤4 · `attribution` |
| `title` | `kicker` · `title` · `sub` |
| `cta` | `line1` · `line2` · `share` (empty = no invitation) · `icon` send\|save\|none · `final` (+`final_font`) · `brand.handle` |
| `paragraph` | `kicker` · `text` |
| `definition` | `term` · `text` · `note` |
| `steps` | `title` · `steps` |
| `timeline` | `title` · `events` `[{when, what}]` |
| `compare` | `left` `{title, points}` · `right` `{title, points}` · `verdict` |
| `qa` | `question` · `answer` |

### 1.5 Cue defaults (what the clock does without you)

| block | default beats |
|---|---|
| `hook` | lead 0 · line1 +0.16 · line2 +0.34 · rule +0.85 · sub +1.00 · emphasis `min(end−1.2, +1.9)` |
| `verse` | first word +0.3, then evenly across `end − 1.9`; highlight at 72 % |
| `answer` | q1 +0.3 · q2 +1.5 · hero +3.0 · after +4.9 · source +5.8 |
| `proof` | seal +0.8 · card *i* at +2.0+1.1·*i* · line1/line2/attribution after the cards |
| `cta` | line1 +0.3 · line2 +1.4 · share +2.7 · final +3.6 · brand `end − 1.55` |
| prose | first sentence +0.35, each next `max(1.80, 0.30·words+0.55)+0.18` later |

If a default puts the last reveal closer than 0.9 s to the cut, `plan.audit` warns: extend the
scene. Do not compress the copy.
