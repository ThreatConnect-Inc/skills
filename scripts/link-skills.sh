#!/usr/bin/env bash
# Symlink every skill in this repo into ~/.claude/skills for live development.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.claude/skills"
mkdir -p "$DEST"
for dir in "$REPO"/plugins/*/skills/*/; do
  name="$(basename "$dir")"
  target="$DEST/$name"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "SKIP $name: $target exists and is not a symlink (move it aside first)"; continue
  fi
  ln -sfn "${dir%/}" "$target"
  echo "linked $name -> ${dir%/}"
done
