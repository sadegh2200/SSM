#!/usr/bin/env bash
# source this once per session, before any build/check/render:
#     source <skill>/scripts/env.sh [workdir-with-node_modules]
# Exports the paths the pipeline uses and checks the toolchain. Safe to re-run. Nothing here is
# machine-specific: every location can be overridden with an environment variable.
#
#   SKILL_DIR     this skill (auto-detected from the location of this file)
#   REEL_WORK     where projects are built          default ./reel-work   (one folder per <slug>)
#   REEL_DELIVER  where finished files are put      default ./reel-deliver
#   HF_WORKDIR    folder that has node_modules/hyperframes (+ playwright)   default ~/reel-sadiqeen
#   TMPDIR        HyperFrames/Playwright scratch (keep it on a disk with space)   default ~/.cache/tmp

export SKILL_DIR="${SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export REEL_WORK="${REEL_WORK:-$PWD/reel-work}"
export REEL_DELIVER="${REEL_DELIVER:-$PWD/reel-deliver}"
export HF_WORKDIR="${1:-${HF_WORKDIR:-$HOME/reel-sadiqeen}}"
export TMPDIR="${TMPDIR:-$HOME/.cache/tmp}"
export HYPERFRAMES_SKIP_SKILLS=1
export HYPERFRAMES_EXTRACT_CACHE_DIR="${HYPERFRAMES_EXTRACT_CACHE_DIR:-$HOME/.cache/hfx}"
mkdir -p "$TMPDIR" "$HYPERFRAMES_EXTRACT_CACHE_DIR" "$REEL_WORK" "$REEL_DELIVER"
[ -x /opt/node22/bin/node ] && export PATH="/opt/node22/bin:$PATH"

ok=1
# ffmpeg: system binary, else the static build shipped by the imageio-ffmpeg wheel (ffprobe still needed for QC)
if ! command -v ffmpeg >/dev/null; then
  IIO_FF=$(python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())" 2>/dev/null || true)
  if [ -n "$IIO_FF" ]; then mkdir -p "$HOME/.cache/reel-bin" && ln -sf "$IIO_FF" "$HOME/.cache/reel-bin/ffmpeg" && export PATH="$HOME/.cache/reel-bin:$PATH"; fi
fi
command -v ffmpeg  >/dev/null || { echo "✗ ffmpeg missing  → sudo apt-get install -y ffmpeg   (or: pip install imageio-ffmpeg)"; ok=0; }
command -v ffprobe >/dev/null || { echo "✗ ffprobe missing → sudo apt-get install -y ffmpeg   (ffprobe ships with it)"; ok=0; }
NODE_V=$(node -v 2>/dev/null || echo none)
case "$NODE_V" in v2[2-9]*|v[3-9]*) ;; *) echo "✗ node >=22 missing (have $NODE_V) → https://nodejs.org/dist/ (linux-x64 tar.xz, extract to /opt/node22) or nvm install 22"; ok=0;; esac
if [ ! -d "$HF_WORKDIR/node_modules/hyperframes" ]; then
  echo "✗ hyperframes not installed in $HF_WORKDIR → mkdir -p $HF_WORKDIR && cd $HF_WORKDIR && npm init -y >/dev/null && npm install --no-audit --no-fund hyperframes@0.8.157 playwright@1.64.1"; ok=0
fi
python3 -c "import numpy" 2>/dev/null || { echo "✗ python numpy missing → pip install numpy   (mix.py, gen_bed.py, cues.py)"; ok=0; }
python3 -c "from PIL import features; import sys; sys.exit(0 if features.check('raqm') else 1)" 2>/dev/null \
  || echo "⚠ Pillow+libraqm missing → font fitting falls back to estimates (pip install pillow; sudo apt-get install -y libfribidi0)"
[ $ok = 1 ] && echo "✓ toolchain ok (node $NODE_V, ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}'), hyperframes in $HF_WORKDIR)"
echo "  SKILL_DIR=$SKILL_DIR  REEL_WORK=$REEL_WORK  REEL_DELIVER=$REEL_DELIVER"
hf() { (cd "$HF_WORKDIR" && npx hyperframes "$@"); }
export -f hf 2>/dev/null
