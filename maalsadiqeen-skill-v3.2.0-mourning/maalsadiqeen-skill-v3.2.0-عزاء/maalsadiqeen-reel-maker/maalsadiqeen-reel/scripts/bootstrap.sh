#!/usr/bin/env bash
# bootstrap.sh — install the toolchain the skill needs, idempotently.
#
#   bash scripts/bootstrap.sh            # check, then install what is missing (pip --user, npm)
#   bash scripts/bootstrap.sh --check    # only report
#   bash scripts/bootstrap.sh --yes      # do not ask for confirmation
#
# Installs: numpy, pillow (font fitting), imageio-ffmpeg (static ffmpeg), hyperframes@0.8.157 +
# playwright in $HF_WORKDIR, then the Chromium headless shell.
# ffprobe is NOT shipped by imageio-ffmpeg: install ffmpeg with the system package manager for a
# real render (the build still works without it; only mixing/rendering need it).
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HF_WORKDIR="${HF_WORKDIR:-$HOME/reel-sadiqeen}"
CHECK=0
YES=0
case "${1:-}" in
  --check) CHECK=1 ;;
  --yes) YES=1 ;;
  "" ) ;;
  *) echo "usage: bash bootstrap.sh [--check|--yes]" >&2; exit 2 ;;
esac

say() { printf '%s\n' "$*"; }
has() { command -v "$1" >/dev/null 2>&1; }

missing=()
has python3 || missing+=("python3")
python3 -c "import numpy" 2>/dev/null || missing+=("numpy")
python3 -c "import PIL" 2>/dev/null || missing+=("pillow")
has ffmpeg || missing+=("ffmpeg")
has ffprobe || missing+=("ffprobe")
has node || missing+=("node")
[ -d "$HF_WORKDIR/node_modules/hyperframes" ] || missing+=("hyperframes")

if [ ${#missing[@]} -eq 0 ]; then
  say "✓ toolchain complete"
  exit 0
fi
say "missing: ${missing[*]}"
if [ "$CHECK" = 1 ]; then
  exit 1
fi

if [ "$YES" = 0 ]; then
  printf 'install now? [y/N] '
  read -r ans </dev/tty || ans=""
  case "$ans" in y|Y|yes|YES) ;; *) say "aborted"; exit 1 ;; esac
fi

pip_install() {
  python3 -m pip install --user --quiet --disable-pip-version-check "$@" \
    || python3 -m pip install --quiet --break-system-packages "$@" \
    || { say "✗ pip failed for $*"; return 1; }
}

for pkg in numpy pillow imageio-ffmpeg; do
  if ! python3 -c "import ${pkg/PIL/PIL/}" 2>/dev/null; then
    say "• pip install $pkg"
    pip_install "$pkg" || true
  fi
done

# static ffmpeg via imageio-ffmpeg (ffprobe still needs the system package)
if ! has ffmpeg; then
  IIO_FF=$(python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())" 2>/dev/null || true)
  if [ -n "$IIO_FF" ]; then
    mkdir -p "$HOME/.cache/reel-bin" && ln -sf "$IIO_FF" "$HOME/.cache/reel-bin/ffmpeg"
    say "• linked static ffmpeg → $HOME/.cache/reel-bin/ffmpeg (add it to PATH via env.sh)"
  else
    say "✗ ffmpeg missing → install with your package manager (apt-get install -y ffmpeg)"
  fi
fi
has ffprobe || say "✗ ffprobe missing → needed for loudness/duration QC (apt-get install -y ffmpeg)"

if has node && [ ! -d "$HF_WORKDIR/node_modules/hyperframes" ]; then
  say "• npm install hyperframes in $HF_WORKDIR"
  mkdir -p "$HF_WORKDIR" && (cd "$HF_WORKDIR" && npm init -y >/dev/null 2>&1 || true \
    && npm install --no-audit --no-fund hyperframes@0.8.157 playwright@1.64.1) \
    || say "✗ npm install failed (check network / registry access)"
  (cd "$HF_WORKDIR" && npx hyperframes browser ensure) || say "⚠ browser ensure failed — run it manually"
fi

say "done. re-run: bash scripts/bootstrap.sh --check"
