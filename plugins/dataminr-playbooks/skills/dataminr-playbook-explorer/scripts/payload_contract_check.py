#!/usr/bin/env python3
"""
Check a trigger payload against the JMESPath job(s) that read it.

Why: agent/webhook playbooks usually start with a JMESPath "extract config" job that reads fields from the
trigger payload. When the UI or caller changes the payload (a key renamed, dropped, or sent as a reference
instead of an object), the run dies in that job with "invalid type for value: None" (a missing key is null,
and join()/length()/in()/sort() on null are hard errors) or, worse, silently carries the text "null"
(to_string(null) == "null") downstream. This script lists, for every expression in the job, which root keys it
reads, which of them are missing from a sample payload, and whether each missing read is guarded.

Usage:
    python3 payload_contract_check.py <playbook.json> <payload.json | '{"inline":"json"}'> [--job "Job name"]

Without --job it checks every JMESPath job whose json_data references #Trigger: (the first hop after a trigger).
Heuristic, not a JMESPath parser: identifiers inside [?...] filters and quoted/backticked literals are ignored.
A "guarded" read is one written as `key || <default>`. Treat UNGUARDED as "will break or yield 'null'".
"""
import json
import re
import sys

FUNC_NEEDS_ARRAY = ("join", "length", "in", "contains", "sort", "sort_by", "max", "min", "sum", "keys", "values", "map")


def strip_literals(expr):
    expr = re.sub(r"`[^`]*`", "``", expr)            # backtick JSON literals
    expr = re.sub(r"'(?:[^'\\]|\\.)*'", "''", expr)  # raw strings
    expr = re.sub(r'"(?:[^"\\]|\\.)*"', '""', expr)  # quoted identifiers
    return expr


def strip_filters(expr):
    """Remove [? ... ] filter bodies (bracket matched) so their @-relative fields are not read as roots."""
    out, i = [], 0
    while i < len(expr):
        if expr.startswith("[?", i):
            depth, j = 1, i + 2
            while j < len(expr) and depth:
                depth += (expr[j] == "[") - (expr[j] == "]")
                j += 1
            out.append("[]")
            i = j
        else:
            out.append(expr[i])
            i += 1
    return "".join(out)


def roots(expr):
    """Yield (root, start_index_in_stripped_expr) for identifiers that start a path (not after '.', not a function)."""
    s = strip_filters(strip_literals(expr))
    for m in re.finditer(r"(?<![\w.@&$])([A-Za-z_][A-Za-z0-9_]*)\b(?!\s*\()", s):
        prev = s[:m.start()].rstrip()
        if prev.endswith("."):
            continue
        yield m.group(1), m.start(), s


def classify(root, pos, s):
    """Guarded if the root (with any trailing path) is followed by '||'."""
    tail = s[pos:]
    path = re.match(r"[A-Za-z0-9_.\[\]*]+", tail)
    after = tail[path.end():].lstrip() if path else tail
    guarded = after.startswith("||")
    head = s[:pos]
    wrappers = [f for f in FUNC_NEEDS_ARRAY if re.search(rf"\b{f}\s*\([^()]*$", head)]
    to_string = bool(re.search(r"to_string\s*\([^()]*$", head))
    return guarded, wrappers, to_string


def expressions_of(job):
    for p in job.get("jobParameterList", []):
        name = p.get("appCatalogItemParameter", {}).get("paramName")
        if name in ("string_expressions", "string_array_expressions"):
            try:
                for kv in json.loads(p.get("value") or "[]"):
                    yield name, kv.get("key"), kv.get("value", "")
            except Exception:
                yield name, "(unparsed)", p.get("value", "")


def main():
    args = [a for a in sys.argv[1:]]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    only = None
    if "--job" in args:
        k = args.index("--job")
        only = args[k + 1]
        del args[k:k + 2]
    pb = json.load(open(args[0]))
    raw = args[1]
    payload = json.loads(raw) if raw.lstrip().startswith("{") else json.load(open(raw))
    keys = set(payload.keys())

    jobs = []
    for j in pb.get("jobList", []):
        app = (j.get("appCatalogItem") or {}).get("programName", "")
        if not app.startswith("TCPB - JMESPath"):
            continue
        if only and j.get("name") != only:
            continue
        data = next((p.get("value", "") for p in j.get("jobParameterList", [])
                     if p.get("appCatalogItemParameter", {}).get("paramName") == "json_data"), "")
        if only or "#Trigger:" in str(data):
            jobs.append(j)
    if not jobs:
        print("No matching JMESPath job found (use --job NAME).")
        sys.exit(2)

    print(f"payload keys ({len(keys)}): {sorted(keys)}")
    bad = 0
    for j in jobs:
        print(f"\n## JMESPath job: {j.get('name')}")
        read, missing_rows = set(), []
        for pname, key, expr in expressions_of(j):
            for root, pos, s in roots(expr):
                read.add(root)
                if root in keys:
                    continue
                guarded, wrappers, to_str = classify(root, pos, s)
                status = "guarded" if guarded else "UNGUARDED"
                note = ""
                if not guarded and wrappers:
                    note = f"-> {'/'.join(wrappers)}() on null is a hard error"
                elif not guarded and to_str:
                    note = "-> to_string(null) yields the text 'null'"
                elif not guarded:
                    note = "-> yields null (check downstream use)"
                missing_rows.append((root, status, key, note))
                bad += status == "UNGUARDED"
        print(f"keys read: {sorted(read)}")
        print(f"present in payload: {sorted(read & keys)}")
        print(f"MISSING from payload: {sorted({r[0] for r in missing_rows})}")
        for root, status, key, note in sorted(missing_rows):
            print(f"  [{status}] {root:<16} read by {key}  {note}")
        extra = sorted(keys - read)
        if extra:
            print(f"payload keys this job never reads: {extra}")
    print(f"\nunguarded reads of missing keys: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
