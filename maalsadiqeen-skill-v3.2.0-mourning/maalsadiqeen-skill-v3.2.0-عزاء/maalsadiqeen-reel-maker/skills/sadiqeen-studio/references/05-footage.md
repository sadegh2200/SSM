# 05 · Footage mode — a recorded take, dressed

The other four references describe a reel that is **drawn**. This one describes the case that
actually arrives most often: the user hands over a phone recording of a scholar in a library and
says «این ویدیو را حرفه‌ای کن».

The studio does not pretend the recording is a page. It keeps the face, and it makes the frame
behave like the brand: measured cuts, a filmic grade, Arabic type that lands on the right syllable,
and sound that sounds like a room, not a phone.

```
python3 footage.py probe  raw.mp4                    # rotation, fps, duration, audio
python3 footage.py pauses raw.mp4                    # where the speaker breathes
python3 footage.py build  edit.json --out deliver/   # the finished cut
```

---

## 1 · Measure before you decide anything

`probe` answers the question the file name cannot: phone files are often **landscape pixels with a
90° display matrix**. Here the source reads `1920×1080, rotation 90` and displays as `1080×1920`.
Every filter in the graph is written for the *displayed* frame, and ffmpeg applies the matrix on
decode — but a `-noautorotate` anywhere, or a `crop` written against the stored size, silently
gives you a sideways reel. Check `probe` first, every time.

`pauses` runs `silencedetect` and gives you the only honest cut points there are. On a 68.7 s take
this was 23 silences and 22 speech onsets: about **52 s of speech inside 69 s**. That gap is where
the editing happens.

## 2 · Cut at the paragraph, cover the cut with a card

The rule: **no word is removed, and no jump cut is ever seen.**

- Head and tail silence are trimmed (`head_trim`, `tail_keep`).
- The pause between two ideas is shortened, not deleted: `lead` 0.12 s stays at each end so the
  sentence still lifts and lands. Removing 0.87 s + 0.85 s + 0.65 s took the picture from 66.6 s to
  64.3 s — three breaths, nothing else.
- Every shortened pause is placed **inside a full-frame brand card**. The card is opaque, so the
  cut is invisible; the splice is inside silence, so it is inaudible. `audit()` fails the build if
  any cut is left uncovered.
- A static single-take camera means a mid-sentence cut *is* visible — so mid-sentence cuts are not
  allowed. Either the pause is long enough to hide a card, or it stays.

Type layers are resolved after the cards: a chyron that would land on a card is pushed to the
card's end (`resolve()`), because two layers of type fighting over one frame is the amateur tell.

## 3 · Grade the phone out of the picture

One chain, in this order, tuned for the mourning palette:

```
scale 1080×1920 lanczos · setsar=1 · fps=30
eq contrast 1.055 · brightness 0.004 · saturation 0.90 · gamma 0.99
colorbalance  warm highlights, cool shadows
curves        gentle S, blacks lifted to 0.012 (never crushed)
unsharp       5:5:0.30
vignette      a=PI/4.6
noise         alls=4:allf=t+u          # grain, not "filter"
zoompan       1 → 1.05 over the whole cut, centred above the eyes
```

The push-in is 5%, not 20%: on a 1080-wide source every percent is resampling. `zoompan` is fed one
output frame per input frame (`d=1`) so the timing stays exact.

## 4 · The type hierarchy

| layer | what | holds the screen |
|---|---|---|
| hook card | brand kicker · the thesis in two lines · one sub line | 2.1 s at 0 |
| chapter cards | «المحور الثاني/الثالث» + a title + series pips | 3.2 s each, over a cut |
| word card | one term at 190 px, held | 3.3 s, over a cut |
| quote card | label in a plate · hand-broken lines · drawn «﴿ ﴾» · note | 3.5 s, over the recitation |
| chyron | kicker · gold hairline · one or two lines, right-aligned at x=986, bottom at y=1420 | 3.5–5.5 s |
| end card | logo · the brand's closing verse · series · handle | 3.3 s after speech |

Rules that came out of the first render being wrong:

- **Height is a design decision, and it is measured.** The band was first anchored at y=1618 —
  the lowest thing above the platform UI — and a pale hand behind the words measured **2.3:1**.
  Raising the block to y=1420 (over the chest, still well above the UI) put the same frame at
  **9.9:1** with no band at all. Same words, same scrim, four hundred pixels of judgement.
- **A local wash is an option, and it is off.** `auto_wash()` measures the frame under each
  chyron and only adds a band — the lightest one that reaches 6.2:1 — if the falloff is not
  enough. On this take it chose none for all seven: the robe is already the backdrop.
- **Type on footage gets a shadow before it gets a box.** A blurred, 0.70-alpha copy of the very
  same layer, offset 2/5 px, follows every diacritic and pulls the ratio up where a pale hand
  crosses behind a word.
- **The scrim is dithered.** An 8-bit gradient over near-black bands visibly: one level per 2.7 px,
  and the eye finds every step. Half a level of noise removes all of it.
- **Ramps are gradients, never rounded rectangles.** A rectangle leaves a corner the eye can find;
  a caption you can see the edges of is a sticker.
- **The chyron snaps to a speech onset** (`"snap": true`): type arrives when he starts talking again,
  not when the editor's arithmetic said so.
- **A Latin handle must be drawn by hand.** `typo` is an RTL shaper: «@maalsadiqeen» comes out as
  «maalsadiqeen@». `_latin()` draws the «@» and the word in that order.
- Cards are balanced around y≈960, not y≈885: a full-frame page with type only in the top half
  reads as a mistake.

## 5 · Sound

No music. A scholar's voice is the content, and a bed under a hadith is the fastest way to make it
cheap. The chain:

```
atrim/setpts per segment → concat
highpass 80 · afftdn nr=8:nf=-48:tn=1
eq 170 Hz +1.4 (room) · 2700 Hz +1.6 (presence) · 6800 Hz −2.2 (sibilance)
acompressor −20 dB · 2.4:1 · 14 ms · 240 ms · makeup 1.6
aresample 48k → apad → loudnorm two-pass −15.5 LUFS / −1.4 dBTP
```

Two-pass, and the **measurement is taken on the processed signal**, not the raw one — otherwise the
compressor's 1.6× makeup changes the loudness after you normalised it. Result on the first
delivery: −15.7 LUFS, −1.0 dBTP.

## 6 · What the report proves

`verify()` measures the finished MP4, not the plan:

- frame, fps, duration, codec;
- integrated loudness and true peak (read the **last** EBU print, not the first partial one);
- **contrast per chyron**, sampled from the real frame: the 92nd-percentile luminance of the area
  around the words against the ink. This is the number that caught the hand at 4.07:1.

## 7 · Spec shape

```jsonc
{
  "source": "raw.mp4", "theme": "mourning", "crf": 21, "push": 0.05,
  "tail_card": 3.3,                       // seconds of end card after the picture ends
  "timeline": {"head_trim": 1.05, "tail_keep": 0.90,
               "cut_at": [16.13, 27.14, 55.57], "lead": 0.12, "max_drop": 0.95},
  "audio": {"lufs": -15.5, "tp": -1.4},
  "beats": [
    {"kind": "card", "design": "hook", "anchor": "start", "dur": 2.1, "title": ["…", "…"]},
    {"kind": "chyron", "at": 3.2, "dur": 4.6, "snap": true, "kicker": "…", "lines": ["…"]},
    {"kind": "card", "design": "chapter", "anchor": "cut", "index": 0, "dur": 3.3},
    {"kind": "card", "design": "quote", "at": 35.3, "dur": 3.7, "quote_lines": ["…"]},
    {"kind": "card", "design": "end", "anchor": "end", "dur": 3.3}
  ]
}
```

`anchor` is `start` · `end` · `cut` (with `index`) · or a numeric `at` in **source** seconds, which
is mapped to output time through the removed pauses.

## 7b · Standalone inserts

Cards built by `footage.py` live inside one cut. When the editor wants pieces to move between
edits, `inserts.py` renders the same pages as **standalone assets**: 3–4 s, silent, MP4 + PNG +
a transparent-type PNG. See SKILL.md § *Inserts* for the contract (silent, hard-cut safe, the
copy gate applies).

## 8 · Cost

| stage | 67.6 s deliverable |
|---|---|
| probe + silencedetect | 20 s |
| adaptive wash (7 graded frame samples) | 10 s |
| overlay PNGs (15 layers) | 2 s |
| audio chain + loudnorm | 55 s |
| picture (`libx264 medium`, crf 21, 15 overlay inputs) | 3 min 20 s |

Deliverable: 1080×1920 · 30.000 fps · 67.60 s · 35.4 MiB · 4.4 Mbit/s · h264 high + aac 192k ·
−15.7 LUFS / −1.0 dBTP · 12/12 checks · chyron contrast 8.80–10.31:1.
