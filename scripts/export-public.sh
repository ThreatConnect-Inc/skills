#!/usr/bin/env bash
# Create a clean, single-commit copy of this repo for publishing, with no internal history
# and without internal-only files (docs/, CLAUDE.md, local pattern files).
# Usage: scripts/export-public.sh <empty-or-new-destination-dir>
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
dest="${1:?usage: scripts/export-public.sh <destination-dir>}"
if [ -e "$dest" ] && [ -n "$(ls -A "$dest")" ]; then echo "ERROR: $dest exists and is not empty" >&2; exit 1; fi
"$repo/validate-skills.sh" >/dev/null || { echo "ERROR: ./validate-skills.sh fails; fix it first" >&2; "$repo/validate-skills.sh" | tail -15 >&2; exit 1; }
mkdir -p "$dest"
rsync -a --exclude .git --exclude .DS_Store --exclude docs --exclude CLAUDE.md --exclude .leak-patterns --exclude .public-exclude \
  --exclude skill-backups --exclude __pycache__ --exclude '.env*' --exclude .claude "$repo/" "$dest/"
# Drop plugins listed in .public-exclude from the export: directory, marketplace entry, README row, VERSIONS rows.
if [ -f "$repo/.public-exclude" ]; then
  python3 - "$dest" "$repo/.public-exclude" <<'PY'
import json, re, shutil, sys
dest, listfile = sys.argv[1], sys.argv[2]
names = [l.strip() for l in open(listfile) if l.strip() and not l.startswith("#")]
for n in names:
    shutil.rmtree(f"{dest}/plugins/{n}", ignore_errors=True)
mp = f"{dest}/.claude-plugin/marketplace.json"
d = json.load(open(mp)); d["plugins"] = [p for p in d["plugins"] if p["name"] not in names]
open(mp, "w").write(json.dumps(d, indent=2) + "\n")
for f in ("README.md", "VERSIONS.md"):
    L = open(f"{dest}/{f}").read().split("\n"); out = []; skip = False
    for l in L:
        if l.startswith("### "):
            skip = any(l.startswith(f"### {n} ") for n in names)
        if skip or any(l.startswith(f"| `{n}` |") for n in names):
            continue
        out.append(l)
    open(f"{dest}/{f}", "w").write("\n".join(out))
PY
  (cd "$dest" && ./validate-skills.sh >/dev/null) || { echo "ERROR: export fails validation after exclusions" >&2; (cd "$dest" && ./validate-skills.sh | tail -10) >&2; exit 1; }
  if grep -rIl -f <(grep -v '^#' "$repo/.public-exclude" | grep .) "$dest" >/dev/null 2>&1; then echo "ERROR: an excluded plugin is still mentioned in the export:" >&2; grep -rIn -f <(grep -v '^#' "$repo/.public-exclude" | grep .) "$dest" | cut -c1-160 >&2; exit 1; fi
fi
[ -f "$dest/LICENSE" ] || echo "WARNING: no LICENSE file; add one (company decision) before publishing" >&2
# Final scan of the export itself, using the local internal-term patterns.
if [ -f "$repo/.leak-patterns" ]; then
  if grep -rIEn -i -f "$repo/.leak-patterns" "$dest" >/dev/null 2>&1; then
    echo "ERROR: internal terms found in export:" >&2; grep -rIEn -i -f "$repo/.leak-patterns" "$dest" | cut -c1-200 >&2; exit 1
  fi
fi
if grep -rIEn '/Users/|/private/tmp/' "$dest" --exclude=validate-skills.sh --exclude=export-public.sh >/dev/null 2>&1; then echo "ERROR: local paths in export" >&2; exit 1; fi
cd "$dest" && git init -q -b main && git add -A && git commit -q -m "Initial release"
echo "Clean export ready: $dest ($(git ls-files | wc -l | tr -d ' ') files, 1 commit)"
