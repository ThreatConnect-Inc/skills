#!/usr/bin/env bash
# Build one zip per skill for upload to claude.ai chat (Settings > Capabilities > Skills).
# Usage: scripts/build-chat-zips.sh [output_dir] [skill ...]
# Default output_dir: ~/Desktop/dataminr-chat-skills. Default skills: every plugin in plugins/.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$HOME/Desktop/dataminr-chat-skills}"
shift || true
mkdir -p "$out"
skills=("$@")
[ ${#skills[@]} -eq 0 ] && for p in "$repo"/plugins/*/; do skills+=("$(basename "$p")"); done
for n in "${skills[@]}"; do
  src="$repo/plugins/$n/skills/$n"
  [ -f "$src/SKILL.md" ] || { echo "SKIP $n: no SKILL.md"; continue; }
  head -6 "$src/SKILL.md" | grep -q '^name:' && head -6 "$src/SKILL.md" | grep -q '^description:' \
    || { echo "SKIP $n: SKILL.md lacks name/description frontmatter"; continue; }
  zip="$out/$n.zip"; rm -f "$zip"
  (cd "$repo/plugins/$n/skills" && zip -qr "$zip" "$n" \
    -x '*.DS_Store' '*/skill-backups/*' '*/__pycache__/*' '*/evals/*')
  note=""
  [ -d "$src/scripts" ] && note=" [WARN: has scripts/ - needs shell, curl and env key files; may not work in chat]"
  grep -rlE '\.env_|TC_KEY' "$src" >/dev/null 2>&1 && note="$note [WARN: refers to local env key files]"
  echo "OK   $n -> $zip ($(du -k "$zip" | cut -f1) KB)$note"
done
