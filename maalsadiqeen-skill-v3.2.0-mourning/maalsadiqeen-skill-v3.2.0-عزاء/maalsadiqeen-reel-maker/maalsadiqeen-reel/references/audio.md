# Audio pipeline (`scripts/mix.py`, `recite.py`, `gen_bed.py`, `cues.py`, `tighten.py`)

Default policy for this brand: **no human or synthetic narrator**. Qurʾan recitation when the reel
contains an āyah; otherwise sound design + ambient bed only. Narration is produced only when the user
asks for it explicitly (then it is a *stem* in the spec, see §7).

The audio must survive the reader: a long-text reel is watched for 50 seconds while reading five
sentences, so the mix is a **room**, not a soundtrack. Nothing may compete with the prose.

## 1 · Spec → mix

```json
"audio": {
  "mode": "silent",                       // silent = text-led (default) | narrated
  "file": "mix.wav",                      // written to <project>/assets/audio/, referenced by <audio>
  "recitation": { "ref": "9:119", "edition": "ar.mahermuaiqly", "at": 3.9 },   // omit when no verse
  "bed": { "gain_db": -7, "duck_db": -9, "fade_out": 2.2, "seed": 7 },        // false → no bed
  "auto_sfx": true,                       // sound design derived from the resolved cues
  "sfx": [ { "name": "chime", "at": 30.4, "gain_db": -16 } ],                 // extra events (optional)
  "stems": [ { "file": "assets/audio/vo-3.wav", "at": 13.4, "gain_db": -1 } ], // narration only on request
  "target_lufs": -15.5, "true_peak_db": -1.5
}
```

`python3 scripts/mix.py <project>` → generates the bed (if any), downloads/trims the recitation (if
`file` missing), lays SFX events, side-chain ducks the bed under the voice bus, masters with a static
gain to the target LUFS + `alimiter` (no one-pass `loudnorm` — it pumps quiet beds). Prints the LUFS
before/after. `--dry-run` prints the event list for review before anything is written.

A 53-second long-text reel produces ≈ 27 events — that is the comfortable ceiling. `--dry-run` is how
you check it.

## 2 · Recitation

`recite.py 9:119 --edition ar.mahermuaiqly --out assets/audio/recite.wav` → trimmed 48 kHz mono WAV,
prints the duration. Budget the verse scene ≥ duration + 1.6 s. Place `at` = the verse scene's first
word cue (`mix.py` does this automatically when `at` is omitted). Ranges: `2:255-257` (≤ 5 āyāt).

Editions: `ar.mahermuaiqly` (default), `ar.alafasy` (alternative); avoid `ar.husary` (slow),
`ar.abdulsamad`, `ar.parhizgar` (CDN stubs). Some very short āyāt are stubs even for Maher (e.g.
103:1) — `recite.py` detects clips < 1 s and tells you to switch to `ar.alafasy`. If the download
fails (no network), ask the user for a file and pass `--recitation path`; `reel.py build` continues
with `--allow-missing-recitation` and prints that the result is **not publishable**.

Word cues: `cues.py assets/audio/recite.wav --words 8 --offset 3.9 --json` → paste into
`scenes[verse].cues.words`. Listen-check two words when possible; adjust by hand if a word lands
early — the eye forgives 100 ms late, never early.

## 3 · Sound-design vocabulary (`auto_sfx`; names = files in `assets/sfx/`)

| moment | sound | gain |
|---|---|---|
| every scene cut | `whoosh-short` | −19 dB |
| hook (+0.34) | `whoosh-short` | −24 dB |
| hook emphasis, first verse word, final line | `sparkle` | −19 / −16 / −14 dB |
| verse highlight | `ping` | −24 dB |
| short-form text reveal (labels, lines, attributions) | `click-soft` | −23 dB |
| strike-through | `pen-scratch` | −14 dB |
| right phrase lands, cards, list items, steps | `pop` | −19…−21 dB |
| 6 s before the hero → hero | `riser` (trimmed 4.03 s, 2.5 s fade-in) → `impact-bass-1` | −23 → −14 dB |
| quote hero | `impact-bass-2` | −16 dB |
| seal | `chime` | −16 dB |
| share plane | `whoosh` | −18 dB |

### The six long-text blocks

| block | sound | gain | why |
|---|---|---|---|
| `paragraph` | `click-soft` per sentence, `-22` on the kicker, `-25` per sentence, `-26` on the note, `-27` on the source | −22…−27 | the page turning, not a drum |
| `definition` | `click-soft` on label, `-22` on the term, per sentence, note, source | −22…−27 | the term gets the loudest click |
| `qa` | `sparkle` on the question (−20), `impact-bass-2` on the first answer sentence (−18), `click-soft` per sentence (−25) | −18…−26 | the answer is the local hero of the scene |
| `steps` | `click-soft` on the title (−23), `pop` per step (−21) | −21/−23 | each step is a small arrival |
| `timeline` | `click-soft` on the title (−24), one per event (−24) | −24 | chronology stays quiet |
| `compare` | `click-soft` on the title (−24) and on both heads (−23), one per **pair** of points (−25), `pop` on the verdict (−19) | −19…−25 | the verdict is the only accent |

**Fewer is better.** If a scene has more than one reveal per 1.5 s, drop its clicks: set
`"auto_sfx": false` and list only the events you want in `sfx`. In prose scenes never add a second
layer — the reader is already working.

## 4 · Bed

`gen_bed.py` synthesises a deterministic D-minor pad + sub drone + soft bells + paper air + synthetic
reverb; chords change on the scene cuts, the brightest voicing lands on the hero cue, bells on the
hero and final cues. −7 dB under everything, ducked −9 dB (ratio 3) under voice/recitation, fades the
last 2.2 s.

A long-text reel has fewer cuts (4–5), so the bed must not loop obviously: keep `seed` fixed per
reel, and if a scene runs past 14 s ask `gen_bed.py` for the longer pad (`--tail 3`) rather than
repeating the 8-second voicing. The bed only has to make sound-on feel finished.

## 5 · Where the beats land in a prose scene

The reader's eye moves on the reveal, not on the cut. That is why the SFX follow the cues:

- a `click-soft` 0.02–0.05 s **before** the sentence appears (the builder already schedules it on the
  cue) — never after;
- no sound on the last sentence of the reel's anchor block — let it land in silence;
- the `qa` impact sits on the first answer sentence, so the viewer hears the answer arrive even
  without reading.

## 6 · Mastering targets

Integrated **−15.5 LUFS** (silent mode) / **−14 LUFS** (narrated), true peak ≤ −1.5 dBTP, 48 kHz.
`verify.py --render` checks the final MP4's loudness; without a render, the mix report is enough for
the kit, but the reel is not delivered until the render matches.

## 7 · Narrated mode (only when asked)

1. Generate voice stems per scene (platform TTS or a human file), one WAV per scene.
2. `tighten.py in.wav out.wav --max-pause 0.26 --tempo 1.06` removes long internal pauses.
3. `cues.py out.wav --lines N --offset <scene start>` → line cues; set scene lengths from the stems.
4. Put the stems in `audio.stems` with their `at`; set `"mode": "narrated"`; mix as usual.
5. Persian narration runs ~20 % longer than Arabic for the same text — rebudget the scenes.

In narrated mode a prose block reads **slower** than the 0.30 s/word default; take the cue list from
`cues.py`, not from the builder's estimate.
