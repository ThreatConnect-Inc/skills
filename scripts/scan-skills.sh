#!/usr/bin/env bash
# Security-scan every skill with NVIDIA SkillSpector (static analysis by default).
#
# Usage:
#   scripts/scan-skills.sh [--root DIR] [--baselines DIR] [--report-dir DIR] [--llm]
#   scripts/scan-skills.sh --accept <skill> "<reason>" [--root DIR] [--baselines DIR]
#
#   --root DIR         folder holding plugins/<plugin>/skills/<skill> trees (default: ./plugins)
#   --baselines DIR    reviewed-and-accepted findings, one <skill>.yaml each (default: ./.skillspector/baselines)
#   --report-dir DIR   keep the JSON reports here (default: a temp folder)
#   --llm              also run SkillSpector's LLM review. This sends skill file contents to the
#                      provider named in SKILLSPECTOR_PROVIDER, so only use it on content that is
#                      already public or approved to share.
#   --accept SKILL R   record every current finding for SKILL as reviewed and accepted, with reason R.
#                      Review the findings first; the baseline hides them from future scans.
#
# Exit code: number of skills with a NEW high or critical finding (or a scan error). 0 = pass.
# New medium/low findings are printed as warnings. Install: see docs below.
#   uv tool install --python 3.13 git+https://github.com/NVIDIA/skillspector.git
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$repo/plugins"; baselines="$repo/.skillspector/baselines"; reports=""; llm=0
accept_skill=""; accept_reason=""

while [ $# -gt 0 ]; do
  case "$1" in
    --root) root="$2"; shift 2 ;;
    --baselines) baselines="$2"; shift 2 ;;
    --report-dir) reports="$2"; shift 2 ;;
    --llm) llm=1; shift ;;
    --accept) accept_skill="${2:?--accept needs a skill name}"; accept_reason="${3:?--accept needs a reason}"; shift 3 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if ! command -v skillspector >/dev/null 2>&1; then
  echo "ERROR: skillspector is not installed." >&2
  echo "  uv tool install --python 3.13 git+https://github.com/NVIDIA/skillspector.git" >&2
  echo "  (needs Python 3.12 or 3.13; uv fetches one if the system Python is older)" >&2
  exit 2
fi

llm_flag=(--no-llm)
if [ "$llm" -eq 1 ]; then
  llm_flag=()
  echo "NOTE: LLM review on: skill contents go to provider '${SKILLSPECTOR_PROVIDER:-<default>}'." >&2
fi

mkdir -p "$baselines"
dirs=()
for d in "$root"/*/skills/*/; do [ -f "$d/SKILL.md" ] && dirs+=("${d%/}"); done
[ ${#dirs[@]} -gt 0 ] || { echo "ERROR: no skills found under $root" >&2; exit 2; }

if [ -n "$accept_skill" ]; then
  for d in "${dirs[@]}"; do
    if [ "$(basename "$d")" = "$accept_skill" ]; then
      skillspector baseline "$d" -o "$baselines/$accept_skill.yaml" --no-llm --reason "$accept_reason"
      exit 0
    fi
  done
  echo "ERROR: skill '$accept_skill' not found under $root" >&2; exit 2
fi

[ -n "$reports" ] || reports="$(mktemp -d)"
mkdir -p "$reports"
failed=0
printf '%-28s %-6s %-15s %-9s %s\n' SKILL SCORE RECOMMENDATION COVERAGE "NEW FINDINGS (H/C | M/L) | accepted"
for d in "${dirs[@]}"; do
  n="$(basename "$d")"; out="$reports/$n.json"
  args=(scan "$d" "${llm_flag[@]}" --format json --output "$out")
  [ -f "$baselines/$n.yaml" ] && args+=(--baseline "$baselines/$n.yaml")
  rc=0; skillspector "${args[@]}" >"$reports/$n.log" 2>&1 || rc=$?
  if [ ! -s "$out" ]; then
    printf '%-28s ERROR (exit %s, see %s)\n' "$n" "$rc" "$reports/$n.log"; failed=$((failed+1)); continue
  fi
  line="$(python3 -I - "$out" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
ra, ac = d.get("risk_assessment", {}), d.get("analysis_completeness") or {}
sev = [i.get("severity", "") for i in d.get("issues", [])]
hc = sum(s in ("HIGH", "CRITICAL") for s in sev); ml = len(sev) - hc
print(f'{ra.get("score","?")}|{ra.get("recommendation","?")}|{ac.get("coverage_percent","?")}%|{hc}|{ml}|{d.get("suppressed_count",0)}')
for i in d.get("issues", []):
    loc = i.get("location", {})
    print(f'    - {i.get("severity")} {i.get("id")} {i.get("pattern")} ({loc.get("file")}:{loc.get("start_line")})')
PY
)"
  head="$(echo "$line" | head -1)"; IFS='|' read -r score rec cov hc ml acc <<<"$head"
  printf '%-28s %-6s %-15s %-9s %s | %s | %s\n' "$n" "$score" "$rec" "$cov" "$hc" "$ml" "$acc"
  echo "$line" | tail -n +2
  [ "${hc:-0}" -gt 0 ] && failed=$((failed+1))
done
echo
echo "Reports: $reports"
if [ "$failed" -gt 0 ]; then
  echo "FAIL: $failed skill(s) with new high/critical findings or scan errors. Review them; accept reviewed false positives with:"
  echo "  scripts/scan-skills.sh --accept <skill> \"<reason>\""
else
  echo "PASS: no new high or critical findings."
fi
exit $(( failed > 125 ? 125 : failed ))
