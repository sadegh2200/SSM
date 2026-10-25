#!/usr/bin/env bash
# bootstrap.sh — make this skill runnable on a bare machine, then prove it.
#
#   bash scripts/bootstrap.sh            # check, then install what is missing
#   bash scripts/bootstrap.sh --check    # report only (exit 1 if something is missing)
#   bash scripts/bootstrap.sh --strict   # also require ffprobe
#
# This exists because a sandbox can be recycled between sessions while the repo
# survives: the skill must be able to rebuild its own toolchain. Everything it
# installs is either in ~/.cache (not in the repo) or a symlink in ~/bin.
#
# What it provides:
#   ffmpeg + ffprobe   static builds (imageio-ffmpeg + ffprobe-static via npm)
#   numpy, pillow      measurements, contact sheets
#   opencv-python<5    face detection (CascadeClassifier vanished in cv2 5.x)
#   dejavu fonts       libass fallback when the skill's own fonts are absent
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$HERE")"
BIN="$HERE/../.bin"
CACHE="$HOME/.cache/sc"
BIN_DIR="$CACHE/bin"
CHECK=0; STRICT=0
case "${1:-}" in
  --check) CHECK=1 ;;
  --strict) STRICT=1 ;;
  "") ;;
  *) echo "usage: bash bootstrap.sh [--check|--strict]" >&2; exit 2 ;;
esac

say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
missing=0

say "== python"
PY=python3
have "$PY" || { say "✗ python3 missing"; exit 1; }
say "  $($PY -V 2>&1)"
need_py() { $PY -c "import $1" 2>/dev/null; }
declare -a WANT=("numpy:numpy" "PIL:pillow" "cv2:opencv-python-headless<5")
for pair in "${WANT[@]}"; do
  mod="${pair%%:*}"; pkg="${pair#*:}"
  if need_py "$mod"; then
    say "  ✓ $mod"
  else
    say "  ✗ $mod ($pkg)"
    missing=1
    if [ "$CHECK" = 0 ]; then
      $PY -m pip install --break-system-packages --quiet --disable-pip-version-check "$pkg" \
        || $PY -m pip install --user --quiet --disable-pip-version-check "$pkg" \
        || { say "  ! pip could not install $pkg"; }
      need_py "$mod" && say "    installed" || say "    still missing"
    fi
  fi
done

say "== ffmpeg / ffprobe"
mkdir -p "$BIN_DIR" "$HOME/bin"
if ! have ffmpeg && [ ! -x "$BIN_DIR/ffmpeg" ] && [ "$CHECK" = 0 ]; then
  $PY -c "import imageio_ffmpeg" 2>/dev/null || \
    $PY -m pip install --break-system-packages --quiet --disable-pip-version-check imageio-ffmpeg 2>/dev/null
  SRC="$($PY -c 'import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())' 2>/dev/null)"
  [ -n "$SRC" ] && cp "$SRC" "$BIN_DIR/ffmpeg" && chmod +x "$BIN_DIR/ffmpeg"
fi
if ! have ffprobe && [ ! -x "$BIN_DIR/ffprobe" ] && [ "$CHECK" = 0 ] && have npm; then
  T="$(mktemp -d)"
  (cd "$T" && npm install --no-audit --no-fund --silent ffprobe-static >/dev/null 2>&1) \
    && cp "$T/node_modules/ffprobe-static/bin/linux/x64/ffprobe" "$BIN_DIR/ffprobe" \
    && chmod +x "$BIN_DIR/ffprobe"
  rm -rf "$T"
fi
for t in ffmpeg ffprobe; do
  if have "$t"; then
    say "  ✓ $t (PATH)"
  elif [ -x "$BIN_DIR/$t" ]; then
    ln -sf "$BIN_DIR/$t" "$HOME/bin/$t"
    case ":$PATH:" in *":$HOME/bin:"*) ;; *) export PATH="$HOME/bin:$PATH" ;; esac
    say "  ✓ $t ($BIN_DIR, linked into ~/bin)"
  else
    if [ "$t" = ffmpeg ] || [ "$STRICT" = 1 ]; then say "  ✗ $t missing"; missing=1
    else say "  • ffprobe missing (verification will be limited)"; fi
  fi
done

say "== fonts"
if ls "$SKILL/assets/fonts"/*.ttf >/dev/null 2>&1; then
  say "  ✓ skill fonts: $(ls "$SKILL/assets/fonts" | tr '\n' ' ')"
else
  say "  ✗ no .ttf in assets/fonts"; missing=1
fi
if ! fc-list 2>/dev/null | grep -qi "dejavu sans"; then
  say "  • DejaVu Sans not installed — Latin captions fall back to libass default"
fi

say "== face cascade"
if [ -s "$SKILL/assets/cascades/haarcascade_frontalface_default.xml" ]; then
  say "  ✓ haarcascade_frontalface_default.xml"
else
  say "  ✗ cascade file missing — reframe will fall back to centre"
  missing=1
fi

say "== ffmpeg filters the pipeline needs"
FF="$(have ffmpeg && command -v ffmpeg || echo "$BIN_DIR/ffmpeg")"
if [ -x "$FF" ]; then
  FILTERS="$("$FF" -hide_banner -filters 2>/dev/null | awk 'NR>8 {print $2}')"
  for f in trim concat scale crop zoompan eq colorbalance unsharp ass loudnorm afftdn aresample; do
    if printf '%s\n' "$FILTERS" | grep -qx "$f"; then
      printf '  ✓ %s\n' "$f"
    else
      printf '  ✗ %s\n' "$f"; missing=1
    fi
  done
else
  say "  ✗ no ffmpeg binary to check"; missing=1
fi

say ""
if [ "$missing" = 1 ]; then
  say "✗ toolchain incomplete — the pipeline will degrade or refuse; see above."
  exit 1
fi
say "✓ toolchain ready. Run:  python3 scripts/studio.py SOURCE.mp4 --out final.mp4"
