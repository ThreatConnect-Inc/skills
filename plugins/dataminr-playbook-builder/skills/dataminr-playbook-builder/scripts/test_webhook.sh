#!/usr/bin/env bash
# Call a webhook-triggered playbook's CURRENT endpoint and save the response next to the backups.
#
# Usage: test_webhook.sh <base_url> <env_file> <groupXid> <backup_root> [--query "a=b&c=d"] [--body '{"k":"v"}'] [--label text]
#
# - Resolves the live endpoint from v3 (it changes every version; a stale one gives an empty 404).
# - Fails loudly on non-2xx instead of reporting "empty output".
# - Saves <backup_root>/<groupXid>/webhook_<UTC ts>_v<version>.txt (status, version, request, body)
# - The playbook must already be ACTIVE (use playbook_ctl.sh activate <groupXid> <draftId>).
set -euo pipefail
BASE_URL="${1:?usage: test_webhook.sh <base_url> <env_file> <groupXid> <backup_root> [--query q] [--body json] [--label text]}"
ENV_FILE="${2:?}"; XID="${3:?}"; ROOT="${4:?}"; shift 4
QUERY=""; BODY=""; LABEL=""
while [ $# -gt 0 ]; do
  case "$1" in --query) QUERY="${2:-}"; shift ;; --body) BODY="${2:-}"; shift ;; --label) LABEL="${2:-}"; shift ;; *) echo "unknown arg $1" >&2; exit 1 ;; esac; shift
done
# shellcheck disable=SC1090
source "$ENV_FILE"; [ -n "${TC_KEY:-}" ] || { echo "ERROR: TC_KEY not set" >&2; exit 1; }
AUTH="Authorization: TC $TC_KEY"

read -r VER ACTIVE EP < <(curl -s -H "$AUTH" -G "$BASE_URL/api/v3/playbooks" --data-urlencode "tql=groupXid EQ \"$XID\"" |
  python3 -I -c "
import sys,json
d=json.load(sys.stdin).get('data',[])
if len(d)!=1: sys.exit('ERROR: expected 1 playbook, got %d' % len(d))
x=d[0]; print(x['version'],x['active'],x.get('endpoint') or 'NONE')")
[ "$ACTIVE" = "True" ] || { echo "ERROR: playbook $XID v$VER is not active; activate first" >&2; exit 1; }
[ "$EP" != "NONE" ] || { echo "ERROR: playbook has no webhook endpoint" >&2; exit 1; }
# curl rejects raw spaces in URLs (exit 3); percent-encode them so "query=a b c" just works.
# Other characters are passed through as given, so pre-encode anything else special (&, #, +, %).
QUERY="${QUERY// /%20}"
URL="$EP${QUERY:+?$QUERY}"

DIR="$ROOT/$XID"; mkdir -p "$DIR"; TS=$(date -u +%Y%m%dT%H%M%SZ); OUTF="$DIR/webhook_${TS}_v${VER}.txt"
if [ -n "$BODY" ]; then
  RESP=$(curl -s -m 300 -w $'\n__HTTP__%{http_code}' -X POST -H "Content-Type: application/json" -d "$BODY" "$URL") || { echo "ERROR: curl failed (exit $?) calling $URL" >&2; exit 1; }
else
  RESP=$(curl -s -m 300 -w $'\n__HTTP__%{http_code}' "$URL") || { echo "ERROR: curl failed (exit $?) calling $URL" >&2; exit 1; }
fi
CODE="${RESP##*__HTTP__}"; OUT="${RESP%$'\n'__HTTP__*}"
{ echo "playbook: $XID v$VER  label: ${LABEL:-none}"; echo "request: ${BODY:+POST body=$BODY }${QUERY:+query=$QUERY}"; echo "http: $CODE"; echo "----"; echo "$OUT"; } > "$OUTF"
echo "HTTP $CODE (v$VER) saved: $OUTF" >&2
case "$CODE" in 2*) [ -n "$OUT" ] || echo "WARNING: HTTP $CODE but EMPTY body — playbook likely failed inside (e.g. missing query param with fail_on_no_results, bad variable ref); check the playbook's execution log" >&2; echo "$OUT" ;; *) echo "ERROR: webhook returned HTTP $CODE (stale endpoint? not active? playbook error?)" >&2; exit 1 ;; esac
