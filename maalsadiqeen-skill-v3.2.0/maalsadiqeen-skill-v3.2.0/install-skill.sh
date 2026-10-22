#!/usr/bin/env bash
# Install (or re-sync) the maalsadiqeen-reel skill, its two first-party tools (arabic-editor,
# hadith-sanad) and the four vendored companion skills into the standard skill locations.
# Idempotent: run it again after any change to a master copy.
#
#   bash install-skill.sh            install / refresh every skill + the ig-reel voice profile
#   bash install-skill.sh --check    verify every installed copy is identical to its master
#
# Masters (edit only these):
#   maalsadiqeen-reel-maker/maalsadiqeen-reel/     the page's own skill
#   maalsadiqeen-reel-maker/skills/<name>/         first-party tools (arabic-editor, hadith-sanad)
#   vendor/skills/<name>/                          third-party skills (see vendor/skills/README.md)
#
# Targets for every skill:
#   <repo>/.claude/skills/<name>        project-scoped (Claude Code and compatible agents)
#   ~/.claude/skills/<name>             user-scoped (Claude Code)
#   ~/.agents/skills/<name>             shared user path (Codex / Copilot / Gemini CLI / ...)
#
# Extra: integrations/ig-reel/voice.md → ~/.claude/instagram/voice.md and ~/.agents/instagram/voice.md
#        (only when the file does not exist yet; an existing profile is never overwritten).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK=0
case "${1:-}" in
  --check) CHECK=1 ;;
  "" ) ;;
  * ) echo "usage: bash install-skill.sh [--check]" >&2; exit 2 ;;
esac

status=0

install_one() {
  local src="$1" name="$2"
  local targets=(
    "$ROOT/.claude/skills/$name"
    "$HOME/.claude/skills/$name"
    "$HOME/.agents/skills/$name"
  )
  if [ ! -f "$src/SKILL.md" ]; then
    echo "✗ master copy not found: $src" >&2
    status=1
    return
  fi
  local n
  n="$(find "$src" -type f | wc -l | tr -d ' ')"
  echo "skill : $name ($n files) ← ${src#$ROOT/}"

  for dst in "${targets[@]}"; do
    if [ "$CHECK" = 1 ]; then
      if [ -d "$dst" ] && diff -r "$src" "$dst" >/dev/null 2>&1; then
        echo "  ✓ $dst"
      else
        echo "  ✗ $dst (missing or out of sync)"
        status=1
      fi
      continue
    fi
    mkdir -p "$(dirname "$dst")"
    rm -rf "$dst"
    cp -a "$src" "$dst"
    if diff -r "$src" "$dst" >/dev/null 2>&1; then
      echo "  ✓ installed → $dst"
    else
      echo "  ✗ copy mismatch → $dst" >&2
      status=1
    fi
  done
}

# 1) the page's own skill
install_one "$ROOT/maalsadiqeen-reel-maker/maalsadiqeen-reel" "maalsadiqeen-reel"

# 2) first-party tools that live beside the pipeline
for src in "$ROOT"/maalsadiqeen-reel-maker/skills/*/; do
  [ -f "$src/SKILL.md" ] || continue
  name="$(awk -F': *' '/^name:[[:space:]]*/{print $2; exit}' "$src/SKILL.md" | tr -d '"')"
  [ -n "$name" ] || { echo "✗ could not read name from $src/SKILL.md" >&2; status=1; continue; }
  install_one "$src" "$name"
done

# 3) vendored companion skills
for src in "$ROOT"/vendor/skills/*/; do
  [ -f "$src/SKILL.md" ] || continue
  name="$(awk -F': *' '/^name:[[:space:]]*/{print $2; exit}' "$src/SKILL.md" | tr -d '"')"
  [ -n "$name" ] || { echo "✗ could not read name from $src/SKILL.md" >&2; status=1; continue; }
  install_one "$src" "$name"
done

# 4) voice profile for ig-reel (never overwrite an existing profile)
VOICE="$ROOT/integrations/ig-reel/voice.md"
if [ -f "$VOICE" ]; then
  for d in "$HOME/.claude/instagram" "$HOME/.agents/instagram"; do
    if [ "$CHECK" = 1 ]; then
      if [ -f "$d/voice.md" ]; then echo "  ✓ voice profile: $d/voice.md"
      else echo "  • voice profile absent: $d/voice.md"; fi
      continue
    fi
    mkdir -p "$d"
    if [ -f "$d/voice.md" ]; then
      echo "  • voice profile kept: $d/voice.md"
    else
      cp "$VOICE" "$d/voice.md"
      echo "  ✓ voice profile → $d/voice.md"
    fi
  done
fi

if [ "$status" = 0 ] && [ "$CHECK" = 0 ]; then
  echo
  echo "Next: source \"$ROOT/.claude/skills/maalsadiqeen-reel/scripts/env.sh\" and follow SKILL.md."
  echo "First-party tools: maalsadiqeen-reel-maker/skills/README.md"
  echo "Companion skills and precedence: vendor/skills/README.md"
fi
exit "$status"
