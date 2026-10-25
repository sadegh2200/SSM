#!/usr/bin/env bash
# Toolchain check (and, on request, install) for sadiqeen-studio.
#
#   bash bootstrap.sh --check    only report what is missing (exit 1 if something is)
#   bash bootstrap.sh            install the Python deps with pip (--user) and say what to do
#                                about ffmpeg if it is missing
#
# The studio needs: python3 ≥ 3.9 + numpy, pillow, uharfbuzz, freetype-py; ffmpeg + ffprobe.
# It does NOT need node, a browser, or a network connection at render time.
set -uo pipefail

PY="${PYTHON:-python3}"
MODE="${1:---check}"
status=0

have() { command -v "$1" >/dev/null 2>&1; }

echo "python : $($PY -V 2>&1)"
$PY - <<'PY' || exit 1
import sys
if sys.version_info < (3, 9):
    print("python : need ≥ 3.9"); sys.exit(1)
PY

check_mod() {
  local mod="$1" pkg="$2"
  if $PY -c "import $mod" >/dev/null 2>&1; then
    echo "  ✓ $pkg"
  else
    echo "  ✗ $pkg"
    echo "$pkg" >> /tmp/_tht_missing
    status=1
  fi
}

: > /tmp/_tht_missing
echo "python packages:"
check_mod numpy numpy
check_mod PIL pillow
check_mod uharfbuzz uharfbuzz
check_mod freetype freetype-py

echo "tools:"
for t in ffmpeg ffprobe; do
  if have "$t"; then echo "  ✓ $t ($(command -v $t))"; else echo "  ✗ $t"; status=1; fi
done

echo "brand skill:"
if [ -n "${SADIQEEN_BRAND_ROOT:-}" ] && [ -f "$SADIQEEN_BRAND_ROOT/config/brand.json" ]; then
  echo "  ✓ $SADIQEEN_BRAND_ROOT (from SADIQEEN_BRAND_ROOT)"
else
  found=""
  for d in "$HOME/.agents/skills/maalsadiqeen-reel" "$HOME/.claude/skills/maalsadiqeen-reel" \
           "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/../maalsadiqeen-reel"; do
    [ -f "$d/config/brand.json" ] && found="$d" && break
  done
  if [ -n "$found" ]; then
    echo "  ✓ $found"
  else
    echo "  ! maalsadiqeen-reel not found — colours fall back to the snapshot, fonts do not."
    echo "    Install it: bash <package>/install-skill.sh   (or set SADIQEEN_BRAND_ROOT)"
    status=1
  fi
fi

if [ "$MODE" = "--check" ]; then
  echo
  [ "$status" = 0 ] && echo "OK — everything the studio needs is here." \
                    || echo "MISSING — see the ✗ lines above."
  exit "$status"
fi

if [ -s /tmp/_tht_missing ]; then
  echo
  echo "installing: $(tr '\n' ' ' < /tmp/_tht_missing)"
  $PY -m pip install --user --quiet $(cat /tmp/_tht_missing) || {
    echo "pip failed. On a Debian/Ubuntu system with an externally-managed python, use:"
    echo "  $PY -m pip install --user --break-system-packages $(cat /tmp/_tht_missing)"
  }
fi

if ! have ffmpeg; then
  cat <<'MSG'

ffmpeg is missing. The studio renders frames without it (use --no-audio), but it cannot
mux audio or measure loudness. Install one of:
  sudo apt-get install -y ffmpeg          # Debian/Ubuntu
  brew install ffmpeg                     # macOS
  # or drop static builds on PATH and re-run this script
MSG
fi

echo
echo "re-check with: bash bootstrap.sh --check"
