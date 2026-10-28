#!/usr/bin/env python3
"""
Print a structured overview of a downloaded ThreatConnect playbook definition
(the JSON produced by fetch_playbook.sh / GET /api/v2/playbooks/{id}).

Usage:
    python3 summarize_playbook.py <path/to/playbook.json>

This only prints facts extracted directly from the JSON (names, ids, app
types, param keys) — it does not interpret prompts or guess at intent. Use it
to get oriented before reading specific jobs' full parameters in detail.
"""
import json
import sys


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        pb = json.load(f)

    print(f"# {pb.get('name', '(unnamed)')}")
    print(f"groupXid: {pb.get('groupXid')}   version: {pb.get('version')}   "
          f"type: {pb.get('type')}")
    desc = pb.get('description') or ''
    if desc:
        print(f"description: {desc}")
    print()

    triggers = pb.get('playbookTriggerList', [])
    print(f"## Trigger(s) ({len(triggers)})")
    for t in triggers:
        print(f"- name: {t.get('name')}")
        print(f"  type: {t.get('type')}   eventType: {t.get('eventType')}   "
              f"scheduleType: {t.get('scheduleType')}")
        if t.get('chatTriggerTypes'):
            print(f"  chatTriggerTypes: {t.get('chatTriggerTypes')}")
        out_vars = t.get('outputVariables')
        if out_vars and out_vars != '[]':
            print(f"  outputVariables: {out_vars}")
        if t.get('httpResponseBody'):
            print(f"  httpResponseBody (what the trigger returns): {t.get('httpResponseBody')}")
    print()

    jobs = pb.get('jobList', [])
    print(f"## Jobs ({len(jobs)})")
    # Group by app type so the pipeline's shape is easy to scan at a glance.
    by_app = {}
    for job in jobs:
        app = job.get('appCatalogItem', {})
        app_name = app.get('programName') or app.get('displayName') or '(unknown app)'
        by_app.setdefault(app_name, []).append(job)

    for app_name, app_jobs in sorted(by_app.items(), key=lambda kv: -len(kv[1])):
        print(f"\n### {app_name}  ({len(app_jobs)})")
        for job in app_jobs:
            print(f"  - [{job.get('id')}] {job.get('name')}")

    print()
    conns = pb.get('playbookConnectionList', [])
    print(f"## Connections: {len(conns)} edges total")
    types = {}
    for c in conns:
        types[c.get('type', '?')] = types.get(c.get('type', '?'), 0) + 1
    for t, count in types.items():
        print(f"  - {t}: {count}")

    scope_vars = pb.get('playbookScopeVariables', [])
    if scope_vars:
        print(f"\n## Scope variables ({len(scope_vars)})")
        for v in scope_vars:
            if isinstance(v, dict):
                print(f"  - {v.get('name', v)}")
            else:
                print(f"  - {v}")

    print()
    print("Next steps: read references/app_type_cheatsheet.md in this skill for what each "
          "app type's jobParameterList params mean, then pull the full params for any job "
          "id above with a small python/jq snippet against this same file.")


if __name__ == '__main__':
    main()
