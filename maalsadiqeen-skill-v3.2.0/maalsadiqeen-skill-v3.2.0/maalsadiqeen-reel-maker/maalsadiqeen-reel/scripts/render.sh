#!/usr/bin/env bash
# bash scripts/render.sh <project_dir> <out.mp4>     — check → render (1 worker) → ffprobe
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(cd "$1" && pwd)"; OUT="$2"
source "$HERE/env.sh" >/dev/null
cd "$HF_WORKDIR"
echo "▶ check"
npx hyperframes check "$PROJ" 2>&1 | grep -E "Check (passed|failed)|✗|error\(s\)" || true
if npx hyperframes check "$PROJ" 2>&1 | grep -q "Check failed"; then echo "✗ fix the check errors before rendering"; exit 1; fi
echo "▶ render (≈4–6 min for 45–60 s at 1 worker; never run two renders at once)"
mkdir -p "$(dirname "$OUT")"
npx hyperframes render "$PROJ" --output "$OUT" --workers 1 2>&1 | grep -vE "^\s*$" | tail -8
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of default=nw=1 "$OUT"
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate -of default=nw=1 "$OUT"
