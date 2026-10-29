#!/usr/bin/env bash
# Playbook lifecycle helper: status / activate / deactivate.
#
# Usage: playbook_ctl.sh <base_url> <env_file> <status|activate|deactivate> <groupXid> [draftId]
#
#   status      prints: id version status active endpoint   (the PUBLISHED version, via v3 by groupXid)
#   activate    with draftId: activates that draft (promotes it; version gets a minor bump).
#               without draftId: activates the currently published version.
#   deactivate  deactivates by groupXid.
# Always prints the resulting status line, including the CURRENT webhook endpoint
# (the endpoint UUID changes with every version — never reuse an old one).
set -euo pipefail
BASE_URL="${1:?usage: playbook_ctl.sh <base_url> <env_file> <status|activate|deactivate> <groupXid> [draftId]}"
ENV_FILE="${2:?}"; ACTION="${3:?}"; XID="${4:?}"; DRAFT="${5:-}"
# shellcheck disable=SC1090
source "$ENV_FILE"; [ -n "${TC_KEY:-}" ] || { echo "ERROR: TC_KEY not set" >&2; exit 1; }
AUTH="Authorization: TC $TC_KEY"

show() {
  curl -s -H "$AUTH" -G "$BASE_URL/api/v3/playbooks" --data-urlencode "tql=groupXid EQ \"$XID\"" |
    python3 -I -c "
import sys,json
d=json.load(sys.stdin).get('data',[])
if len(d)!=1: sys.exit('ERROR: expected 1 playbook for $XID, got %d' % len(d))
x=d[0]; print(x['id'],'v'+x['version'],x['status'],'active='+str(x['active']),x.get('endpoint') or 'no-endpoint')"
}
call() {  # $1 = path
  OUT=$(curl -s -X POST -H "$AUTH" "$BASE_URL/api/v2/playbooks/$1")
  echo "$OUT" | python3 -I -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='Success' else d)" \
    || { echo "ERROR: $ACTION failed: $OUT" | head -c 600 >&2; exit 1; }
}
case "$ACTION" in
  status) ;;
  activate) call "${DRAFT:-$XID}/activate"; sleep 3 ;;
  deactivate) call "$XID/deactivate" ;;
  *) echo "unknown action: $ACTION" >&2; exit 1 ;;
esac
show
