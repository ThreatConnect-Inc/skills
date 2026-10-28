#!/usr/bin/env bash
# Resolve a ThreatConnect playbook identifier (numeric id, groupXid, or name search)
# to its full definition, and save it as pretty-printed JSON.
#
# Usage:
#   fetch_playbook.sh <base_url> <env_file> <identifier> [out_dir]
#
#   base_url    e.g. https://<instance>.threatconnect.com  (no trailing slash)
#   env_file    path to a .env file containing TC_KEY=APIV2:...
#   identifier  a numeric playbook id, an 8-char groupXid, or a name/partial name to search
#   out_dir     where to save the result (default: ./playbook-export)
#
# Why this exists: the ThreatConnect v3 API can list/filter playbooks (by groupXid,
# name, etc.) but cannot return a single playbook's full job definition
# (GET /api/v3/playbooks/{id} => "0x1005 This operation is not supported").
# The v2 API CAN return the full definition (GET /api/v2/playbooks/{id}), but has
# no equivalent TQL-based lookup. So resolving an id always goes through v3 first,
# then the actual download goes through v2.

set -euo pipefail

BASE_URL="${1:?usage: fetch_playbook.sh <base_url> <env_file> <identifier> [out_dir]}"
ENV_FILE="${2:?usage: fetch_playbook.sh <base_url> <env_file> <identifier> [out_dir]}"
IDENTIFIER="${3:?usage: fetch_playbook.sh <base_url> <env_file> <identifier> [out_dir]}"
OUT_DIR="${4:-./playbook-export}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
if [ -z "${TC_KEY:-}" ]; then
  echo "ERROR: TC_KEY not set after sourcing $ENV_FILE" >&2
  exit 1
fi

AUTH_HEADER="Authorization: TC $TC_KEY"
mkdir -p "$OUT_DIR"

resolve_by_tql() {
  # $1 = tql expression (already appropriately quoted for --data-urlencode)
  curl -s -H "$AUTH_HEADER" -G "$BASE_URL/api/v3/playbooks" --data-urlencode "tql=$1"
}

NUMERIC_ID=""

if [[ "$IDENTIFIER" =~ ^[0-9]+$ ]]; then
  NUMERIC_ID="$IDENTIFIER"
  echo "Identifier looks like a numeric id already: $NUMERIC_ID" >&2
elif [[ "$IDENTIFIER" =~ ^[A-Za-z0-9]{6,12}$ ]]; then
  echo "Identifier looks like a groupXid, resolving via v3..." >&2
  RESP=$(resolve_by_tql "groupXid EQ \"$IDENTIFIER\"")
  COUNT=$(echo "$RESP" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('data',[])))")
  if [ "$COUNT" != "1" ]; then
    echo "ERROR: expected exactly 1 match for groupXid=$IDENTIFIER, got $COUNT" >&2
    echo "$RESP" | python3 -m json.tool >&2
    exit 1
  fi
  NUMERIC_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['data'][0]['id'])")
  echo "Resolved groupXid $IDENTIFIER -> numeric id $NUMERIC_ID" >&2
else
  echo "Identifier doesn't look like an id or xid — searching by name: \"$IDENTIFIER\"" >&2
  RESP=$(resolve_by_tql "name CONTAINS \"$IDENTIFIER\"")
  COUNT=$(echo "$RESP" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('data',[])))")
  if [ "$COUNT" = "0" ]; then
    echo "ERROR: no playbooks matched name CONTAINS \"$IDENTIFIER\"" >&2
    exit 1
  elif [ "$COUNT" != "1" ]; then
    echo "Multiple playbooks matched \"$IDENTIFIER\" — pick one by id or groupXid and re-run:" >&2
    echo "$RESP" | python3 -c "
import json, sys
for p in json.load(sys.stdin)['data']:
    print(f\"  id={p['id']}  groupXid={p.get('groupXid')}  name={p.get('name')}  updated={p.get('updated')}\", file=sys.stderr)
"
    exit 1
  fi
  NUMERIC_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['data'][0]['id'])")
  XID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['data'][0].get('groupXid',''))")
  echo "Resolved name match \"$IDENTIFIER\" -> numeric id $NUMERIC_ID (groupXid=$XID)" >&2
fi

echo "Downloading full definition for playbook id $NUMERIC_ID via v2 API..." >&2
RAW_JSON=$(curl -s -H "$AUTH_HEADER" "$BASE_URL/api/v2/playbooks/$NUMERIC_ID")

# Sanity check: v2 errors come back as {"status":..., ...} without a "name" key most of the time,
# a real playbook definition always has "name" and "jobList".
if ! echo "$RAW_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'jobList' in d" 2>/dev/null; then
  echo "ERROR: v2 response didn't look like a playbook definition — got:" >&2
  echo "$RAW_JSON" | head -c 1000 >&2
  exit 1
fi

SLUG=$(echo "$RAW_JSON" | python3 -c "
import json, re, sys
d = json.load(sys.stdin)
name = re.sub(r'[^A-Za-z0-9]+', '-', d.get('name','playbook')).strip('-').lower()
xid = d.get('groupXid','noxid')
print(f'{name}_{xid}')
")
OUT_FILE="$OUT_DIR/${SLUG}.json"
echo "$RAW_JSON" | python3 -m json.tool > "$OUT_FILE"

echo "Saved: $OUT_FILE" >&2
echo "$OUT_FILE"
