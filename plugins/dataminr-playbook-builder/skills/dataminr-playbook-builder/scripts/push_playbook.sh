#!/usr/bin/env bash
# Safely push an edited ThreatConnect playbook definition back to an instance.
# Also used for reverting: push a saved backup file the same way.
#
# Usage:
#   push_playbook.sh <base_url> <env_file> <edited.json> <backup_root> [--yes] [--brief] [--note "why"]
#   --brief  print a semantic summary (changed jobs + connection changes, ids ignored) instead of the
#            raw text diff, which is huge because every id renumbers. Needs dataminr-playbook-explorer's
#            diff_playbooks.py (override the path with DIFF_PLAYBOOKS=...); falls back to the raw diff.
#
# What it does, in order:
#   1. Reads groupXid from <edited.json> and resolves the CURRENT numeric id via v3
#      (the numeric id changes after every update; groupXid is the stable identifier).
#   2. Downloads the live definition and saves it to
#      <backup_root>/<groupXid>/<UTC timestamp>_before.json   (rollback point)
#   3. Prints a diff of live vs edited. Without --yes it stops here (dry run).
#   4. POSTs the edited definition to /api/v2/playbooks/<id>  (PUT is 405 on v2).
#   5. Re-fetches, saves <timestamp>_after.json, and appends to <backup_root>/<groupXid>/CHANGELOG.md.
#
# The TC_KEY is never printed.
set -euo pipefail

BASE_URL="${1:?usage: push_playbook.sh <base_url> <env_file> <edited.json> <backup_root> [--yes] [--note text]}"
ENV_FILE="${2:?}"; EDITED="${3:?}"; BACKUP_ROOT="${4:?}"; shift 4
YES=0; NOTE=""; BRIEF=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) YES=1 ;;
    --brief) BRIEF=1 ;;
    --note) NOTE="${2:-}"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac; shift
done

[ -f "$ENV_FILE" ] || { echo "ERROR: env file not found: $ENV_FILE" >&2; exit 1; }
[ -f "$EDITED" ] || { echo "ERROR: edited file not found: $EDITED" >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"
[ -n "${TC_KEY:-}" ] || { echo "ERROR: TC_KEY not set in $ENV_FILE" >&2; exit 1; }
AUTH="Authorization: TC $TC_KEY"

XID=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['groupXid'])" "$EDITED")
NAME=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" "$EDITED")

RESP=$(curl -s -H "$AUTH" -G "$BASE_URL/api/v3/playbooks" --data-urlencode "tql=groupXid EQ \"$XID\"")
ID=$(echo "$RESP" | python3 -I -c "
import json,sys
d=json.load(sys.stdin).get('data',[])
if len(d)!=1: sys.exit('ERROR: expected 1 playbook for groupXid $XID, got %d' % len(d))
print(d[0]['id'])")

TS=$(date -u +%Y%m%dT%H%M%SZ)
DIR="$BACKUP_ROOT/$XID"; mkdir -p "$DIR"
BEFORE="$DIR/${TS}_before.json"
curl -s -H "$AUTH" "$BASE_URL/api/v2/playbooks/$ID" | python3 -I -m json.tool > "$BEFORE"
python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); assert d.get('groupXid')==sys.argv[2]" "$BEFORE" "$XID" \
  || { echo "ERROR: live download did not look like playbook $XID" >&2; exit 1; }
echo "Playbook: $NAME ($XID) live id $ID" >&2
echo "Backup saved: $BEFORE" >&2

LOGLVL=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1])).get('logLevel'))" "$EDITED")
case "$LOGLVL" in DEBUG|TRACE) ;; *) echo "WARNING: logLevel is '$LOGLVL'. Dev/test playbooks should be DEBUG or TRACE (only INFO/WARN for production)." >&2 ;; esac
python3 -I -m json.tool "$EDITED" > "$DIR/${TS}_edited.json"
echo "---- diff (live -> edited) ----" >&2
DIFFPY="${DIFF_PLAYBOOKS:-$HOME/.claude/skills/dataminr-playbook-explorer/scripts/diff_playbooks.py}"
if [ "$BRIEF" = "1" ] && [ -f "$DIFFPY" ]; then
  python3 "$DIFFPY" "$BEFORE" "$DIR/${TS}_edited.json" 2>&1 | awk '/^=== (CONNECTIONS|SUMMARY)/{p=1} p' >&2 || true
else
  diff -u "$BEFORE" "$DIR/${TS}_edited.json" >&2 || true
fi
echo "-------------------------------" >&2

if [ "$YES" != "1" ]; then
  echo "DRY RUN: nothing pushed. Re-run with --yes after the user approves the diff." >&2
  exit 0
fi

OUT=$(curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" --data @"$EDITED" "$BASE_URL/api/v2/playbooks/$ID")
STATUS=$(echo "$OUT" | python3 -I -c "import json,sys; print(json.load(sys.stdin).get('status'))" 2>/dev/null || echo unparseable)
if [ "$STATUS" != "Success" ]; then
  echo "ERROR: update failed: $OUT" | head -c 800 >&2; exit 1
fi
NEWID=$(echo "$OUT" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['data']['playbook'][0]['id'])")
VER=$(echo "$OUT" | python3 -I -c "import json,sys; print(json.load(sys.stdin)['data']['playbook'][0]['version'])")

curl -s -H "$AUTH" "$BASE_URL/api/v2/playbooks/$NEWID" | python3 -I -m json.tool > "$DIR/${TS}_after.json"
{
  echo "## $TS — $NAME ($XID) -> version $VER, id $ID -> $NEWID"
  echo "- instance: $BASE_URL"
  echo "- note: ${NOTE:-none}"
  echo "- before: ${TS}_before.json   after: ${TS}_after.json"
  echo
} >> "$DIR/CHANGELOG.md"
echo "Pushed. version $VER, new id $NEWID. Logged in $DIR/CHANGELOG.md" >&2
echo "$DIR/${TS}_after.json"
