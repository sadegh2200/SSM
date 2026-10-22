# Troubleshooting (toolchain, sandboxes, renders)

Run `source scripts/env.sh` first — it prints what is missing and the exact install command, and exports
`SKILL_DIR`, `REEL_WORK`, `REEL_DELIVER`, `HF_WORKDIR` (override any of them before sourcing).

| problem | cause → fix |
|---|---|
| `node: command not found` / Node < 22 | HyperFrames needs Node ≥ 22. `curl -fsSL https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.xz -o /tmp/node.tar.xz && sudo mkdir -p /opt/node22 && sudo tar -xJf /tmp/node.tar.xz -C /opt/node22 --strip-components=1`; env.sh adds it to PATH |
| `hyperframes` not found | install in a work dir: `cd ~/reel-sadiqeen && npm init -y && npm install hyperframes@0.8.157 playwright@1.64.1`; always run `npx hyperframes` from that dir (env.sh exports `HF_WORKDIR`) |
| `ffmpeg: not found` | `sudo apt-get install -y ffmpeg` |
| Ephemeral sandbox restarted | apt packages, /opt/node22, node_modules and ~/.cache vanish; workspace files survive. Re-run env.sh and the installs; never assume a previous toolchain exists |
| `build_reel.py` / `post_kit.py` raise `SyntaxError: f-string expression part cannot include a backslash` | an old copy of the scripts on Python < 3.12 — update the skill; the current scripts run on Python ≥ 3.9 |
| `recite.py` cannot reach the CDN | download the ayah mp3 elsewhere and run `recite.py 9:119 --from-files a.mp3`, or set `audio.recitation.file` to a local WAV |
| `Failed to launch the browser process … Code: 127` | missing shared libs for Chrome headless shell → `ldd ~/.cache/hyperframes/chrome/*/*/chrome-headless-shell \| grep "not found"` then `sudo apt-get install -y` the libs (libnss3 libatk-bridge2.0-0 libxkbcommon0 libgbm1 libasound2 …) |
| `Low disk space … /tmp` during render | `export TMPDIR=~/.cache/tmp` (env.sh does) |
| `Browser session never ran` in check | same as 127 above; also happens when a previous render is still running — never run two browsers/renders at once |
| snapshot `Unknown flag` | the flags are `--at t1,t2 -o <dir> --no-end` (no `-t`, no `--out`) |
| Lint ⚠ `nested_structure_needs_subcomposition` on every `<section>` | expected: the builder emits a single-file project (scenes = `<section>` clips inside the root). It is a warning, renders are unaffected (`render.sh` fails only on `Check failed`). Planned improvement: emit one sub-composition file per scene (`data-composition-src`) so the Studio timeline shows one row per scene |
| Lint ✗ `audio_src_not_found: assets/audio/mix.wav` | you ran `check`/`lint` before `mix.py` — build the soundtrack first (or set `audio.file` to an existing file) |
| Lint `negative z-index` | layer by DOM order; `isolation: isolate` does not silence the lint |
| Blank render, check passes | `dir="rtl"` on `<html>` — remove it |
| mix.py hangs | should not happen (finite `apad`); if it does, kill ffmpeg and check that every input file exists and that no SFX name is misspelled |
| recitation download fails | network blocked → ask the user for a recitation file and pass `--recitation path`, or set `audio.recitation.file` |
| `recite.py` says "looks like a stub" | that edition is empty on the CDN → `--edition ar.alafasy` |
| Pillow has no raqm | `pip install pillow` (wheels bundle libraqm) **and** `sudo apt-get install -y libfribidi0` (raqm loads it at runtime); otherwise font fitting uses conservative estimates — sizes come out ~10 % smaller |
| Fonts render as boxes | the project must have `assets/fonts/*.ttf` copied (build_reel.py does); `document.fonts.ready` must resolve before `build()` |
| Persian/other-language reel | Persian runs ~20 % longer; keep `nowrap` lines short; use `font: "amiri"` for Persian prose, Kufi for headlines |
| Exec bits lost on `.sh` | invoke with `bash scripts/render.sh …` |
| Render takes > 8 min | normal range is 3.5–6 min at `--workers 1` for 45–60 s; longer means a stuck browser → kill and retry |
