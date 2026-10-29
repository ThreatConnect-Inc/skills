#!/usr/bin/env python3
"""
Compare two downloaded ThreatConnect playbook definitions (the JSON produced
by fetch_playbook.sh) and report genuine content differences in their jobs'
prompts/templates — filtering out the noise of internal job-id references
differing between the two playbooks, which is expected and not meaningful.

Usage:
    python3 diff_playbooks.py <playbook_a.json> <playbook_b.json> [job_name ...]

If no job names are given, compares every job present (by name) in both
playbooks across ALL of each job's parameters (every app type: Base Agent
prompts, JMESPath expressions, Merge `output_array`, Logger `log_message`,
If/Else operands, fetch `params`, Template Builder inputs, ...), then compares
the connection graph by job NAME (so renumbered ids do not matter). Pass
specific job names to narrow the per-job comparison.

An earlier version only looked at a short allow-list of params for four app
types, so a changed Merge or Logger job produced "no differences". It now
reports a one-line summary of every job that changed, so a job can no longer
be silently skipped.

Playbook A is treated as the baseline ("-" side); playbook B is the "+" side
in the diff output. Get this the right way round for your actual question —
e.g. if B is meant to receive A's changes, a "+" line is something B is
missing, a "-" line is something only A has.
"""
import json
import re
import sys
import difflib


JOB_ID_REF_RE = re.compile(r'#(App|Global|Trigger):(\d+|0):')


def normalize(text):
    """Replace job-id references with a placeholder so they don't show up
    as diff noise when comparing two playbooks with different internal ids."""
    return JOB_ID_REF_RE.sub(r'#\1:<id>:', text)


def get_job(pb, name):
    for job in pb.get('jobList', []):
        if job.get('name') == name:
            return job
    return None


def get_param(job, pname):
    if not job:
        return None
    for p in job.get('jobParameterList', []):
        if p.get('appCatalogItemParameter', {}).get('paramName') == pname:
            return p.get('value', '')
    return None


def all_params(job):
    """{param key: value} for every parameter of a job. The key is the app's
    paramName; params without one (older apps) are keyed by position."""
    out = {}
    for i, p in enumerate((job or {}).get('jobParameterList', [])):
        key = (p.get('appCatalogItemParameter') or {}).get('paramName') or f'param[{i}]'
        if key in out:
            key = f'{key}#{i}'
        out[key] = p.get('value')
    return out


def edge_set(pb):
    """Connections as (type, source name, target name) using job/trigger NAMES."""
    names = {j['id']: j['name'] for j in pb.get('jobList', [])}
    tnames = {t['id']: t.get('name', 'trigger') for t in pb.get('playbookTriggerList', [])}
    edges = set()
    for c in pb.get('playbookConnectionList', []):
        src = names.get(c.get('sourceJobId')) or tnames.get(c.get('sourceTriggerId')) or 'trigger'
        dst = names.get(c.get('targetJobId')) or tnames.get(c.get('targetTriggerId')) or 'trigger'
        edges.add((c.get('type'), src, dst))
    return edges


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]
    only_names = set(sys.argv[3:]) if len(sys.argv) > 3 else None

    pb_a = json.load(open(path_a))
    pb_b = json.load(open(path_b))

    names_a = {job['name'] for job in pb_a.get('jobList', [])}
    names_b = {job['name'] for job in pb_b.get('jobList', [])}
    common = names_a & names_b
    only_in_a = names_a - names_b
    only_in_b = names_b - names_a

    if only_names:
        common = common & only_names

    print(f"# Comparing {path_a} (baseline, '-') vs {path_b} ('+')\n")

    if not only_names:
        if only_in_a:
            print(f"Jobs only in {path_a}: {sorted(only_in_a)}")
        if only_in_b:
            print(f"Jobs only in {path_b}: {sorted(only_in_b)}")
        if only_in_a or only_in_b:
            print()

    any_diff = False
    changed_jobs = {}
    for name in sorted(common):
        job_a = get_job(pb_a, name)
        job_b = get_job(pb_b, name)
        pa, pb_params = all_params(job_a), all_params(job_b)
        for field in sorted(set(pa) | set(pb_params)):
            val_a = pa.get(field)
            val_b = pb_params.get(field)
            if val_a is None and val_b is None:
                continue
            val_a = str(val_a or '')
            val_b = str(val_b or '')
            norm_a, norm_b = normalize(val_a), normalize(val_b)
            if norm_a == norm_b:
                continue
            any_diff = True
            changed_jobs.setdefault(name, []).append(field)
            print(f"=== DIFF: {name} :: {field} ===")
            diff = list(difflib.unified_diff(
                norm_a.splitlines(), norm_b.splitlines(), lineterm=''))
            for line in diff[:80]:
                print(line)
            if len(diff) > 80:
                print(f'... ({len(diff) - 80} more diff lines, truncated)')
            print()

    # Scope variables (e.g. an FTL/HTML template or a long shared prompt stored as a playbook-level variable)
    # live outside jobList, so the per-job loop above never sees them. Compare them by name too.
    if not only_names:
        sv_a = {v.get('name'): str(v.get('value') or '') for v in pb_a.get('playbookScopeVariables', [])}
        sv_b = {v.get('name'): str(v.get('value') or '') for v in pb_b.get('playbookScopeVariables', [])}
        for name in sorted(set(sv_a) | set(sv_b)):
            if name not in sv_a or name not in sv_b:
                any_diff = True
                print(f"=== SCOPE VARIABLE only in {'B' if name in sv_b else 'A'}: {name} ===\n")
                continue
            na, nb = normalize(sv_a[name]), normalize(sv_b[name])
            if na == nb:
                continue
            any_diff = True
            print(f"=== DIFF: scope variable {name} ===")
            diff = list(difflib.unified_diff(na.splitlines(), nb.splitlines(), lineterm=''))
            for line in diff[:80]:
                print(line)
            if len(diff) > 80:
                print(f'... ({len(diff) - 80} more diff lines, truncated)')
            print()

    # Connection graph, compared by name (ids differ between any two playbooks).
    if not only_names:
        ea, eb = edge_set(pb_a), edge_set(pb_b)
        added, removed = sorted(eb - ea), sorted(ea - eb)
        if added or removed:
            any_diff = True
            print("=== CONNECTIONS (by job name) ===")
            for t, s_, d_ in removed:
                print(f"- {t}: {s_} -> {d_}")
            for t, s_, d_ in added:
                print(f"+ {t}: {s_} -> {d_}")
            print()

    print("=== SUMMARY ===")
    if changed_jobs:
        for name, fields in sorted(changed_jobs.items()):
            print(f"changed: {name}  ({', '.join(fields)})")
    if not any_diff:
        print("No content differences found (after filtering job-id-reference noise).")


if __name__ == '__main__':
    main()
