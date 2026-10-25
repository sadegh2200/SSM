# 3 · Sound — the bed, the cues, the one number

A «مع الصادقين» reel is quiet. The sound is there so the silence after it feels deliberate.

## 3.1 The three layers

| layer | level | source |
|---|---|---|
| bed | −7 dB before the master, ducked under any voice | the brand's `gen_bed.py` (deterministic D-minor pad, chords change on the cuts, brightest chord on the hero, resolve on the last cut) |
| voice | 0 dB, no reverb added | recited āyah (`ar.mahermuaiqly`) or, when the user explicitly asks, a recorded narration |
| cues | −12 … −30 dB per cue | the brand's SFX library, fired by the picture |

Master: **−15.5 LUFS** integrated (−14 when the user asks for louder), true peak ≤ **−1.5 dBTP**,
LRA 11. `loudnorm` + `alimiter` do it in one pass; `verify` measures `ebur128` afterwards and the
report prints the number.

## 3.2 Cues come from the picture, not from a mood

Every block returns `(time, sfx, gain)` while it is being drawn. That is why there is no "sound
design" stage to forget:

| event | cue | gain |
|---|---|---|
| a word lands | `click-soft` | −30 |
| a hero line lands | `impact-bass-1` | −12 (impact) / −17 (closing line) |
| the strike on a wrong reading | `pen-scratch` | −18 |
| the gold highlight on a verse | `sparkle` | −16 |
| the seal lands | `chime` | −14 |
| every cut | `whoosh-short` | −26 |
| 0.6 s before a hero | `riser` | −24 |

If a block did not ask for a sparkle, there is none. The cue list is written next to the silent
master (`video-silent.mp4.cues.json`) and deleted once the mix exists.

## 3.3 Ducking

The bed is side-chained to the voice: 50 ms envelope, −9 dB depth, 20 ms attack, ~320 ms release
(one-pole, `a = 0.0015`). Without the voice the bed plays straight — a pad that pumps under
nothing is the sound of a template.

## 3.4 Recitation

```bash
python3 <reel>/scripts/recite.py 9:119 --out recite.wav     # when the network allows it
python3 studio.py build spec.json --out deliver/            # audio.recitation in the spec
```

- a verse scene must be ≥ recitation length + 1.6 s (+0.8 with a label);
- recitation is raw: no reverb, no compression, no fades inside the āyah;
- if the fetch fails, the studio does **not** substitute a synthetic voice — it renders the reel
  with the bed only and the summary says the recitation is missing.

## 3.5 Narration (only when asked)

A synthetic narrator is against the brand's doctrine. If the user asks for their own voice:

1. the voice is the master; the bed ducks under it (−9 dB);
2. cues reduce to cut whooshes only;
3. target −14 LUFS, true peak ≤ −1.5 dBTP;
4. the reel must still make sense muted — if it does not, the copy is not written yet.

## 3.6 Numbers to check, not to feel

| what | how | wanted |
|---|---|---|
| integrated loudness | `ffmpeg -af ebur128` | −15.5 ±1.2 LUFS |
| true peak | same | ≤ −1.0 dBTP |
| a clip that “sounds quiet” on a phone | compare `I:` between the bed and a competitor | within 1 LU of −15.5 |
| a cue that jumps | listen at 30 % volume | no cue above the bed by more than 18 dB |
