# SFX & asset credits

## Bundled sound effects (`assets/sfx/`)

| file | origin | licence |
|---|---|---|
| `chime.mp3`, `click-soft.mp3`, `impact-bass-1.mp3`, `impact-bass-2.mp3`, `ping.mp3`, `pop.mp3`, `riser.mp3`, `sparkle.mp3`, `whoosh.mp3`, `whoosh-short.mp3` | copied from the HyperFrames `media-use/audio` bundled library, which sources them from [Pixabay](https://pixabay.com/sound-effects/) | [Pixabay Content License](https://pixabay.com/service/license-summary/) — commercial and non-commercial use, modification and redistribution inside derivative works, no attribution required (given here for transparency) |
| `pen-scratch.wav` | synthesised procedurally (band-passed noise burst, seeded) by this skill's author | no third-party rights |

Only the files that `scripts/mix.py` actually uses are bundled (`whoosh.mp3` and `whoosh-short.mp3` are
currently the same recording under the two names the mixer expects). Everything else in the soundtrack is
generated at build time: the ambient bed by `scripts/gen_bed.py`, Qurʾan recitation (when a verse is on
screen) fetched by `scripts/recite.py` from the AlQuran Cloud CDN (`cdn.islamic.network`, free to use; the
reciter is credited in the beat sheet).

## Fonts (`assets/fonts/`, `assets/remotion-template/public/fonts/`)

Amiri, Amiri Quran, Noto Kufi Arabic, Noto Naskh Arabic, Vazirmatn — SIL Open Font License 1.1.

## Other bundled files

- `assets/gsap.min.js` — GSAP (Webflow "no charge" licence; bundled for offline builds as HyperFrames does).
- `assets/brand/logo.png`, `logo-wm.png` — the page's own logo (property of @maalsadiqeen); the watermark
  copy is identical today — replace `logo-wm.png` with a lighter version if a softer watermark is wanted.
- `assets/remotion-template/public/audio/*.wav` — synthesised by `scripts/make_audio.py` (no third-party rights).
