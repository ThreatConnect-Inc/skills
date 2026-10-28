#!/usr/bin/env python3
"""
Run a playbook's JMESPath expression OFFLINE against a real sample of the data
it will receive, so null-handling and shape bugs show up before a push or a
live run.

Usage:
    python3 jmespath_local_test.py <expression | @file> <data.json> \
        [--sub 'name-or-ref=value' ...] [--head N]

  expression   the expression text, or @path to read it from a file
  data.json    a sample of the job's input (e.g. the raw response of the same
               GET the playbook's fetch job makes, saved with curl)
  --sub        replace a ThreatConnect variable reference in the expression
               with a literal. The key may be the full reference or any
               substring of it, e.g.  --sub 'rpt.assoc_groups=true'
               replaces #App:123:rpt.assoc_groups!String with  true
               (the gate pattern: `#App:..:flag!String` && (...)).
  --head N     print only the first N characters of the result (default 3000)

Requires the `jmespath` package (pip install jmespath; use a venv if the
system Python is locked down).

IMPORTANT LIMITS
  * This is the STANDARD JMESPath engine plus APPROXIMATE stubs of the TC
    custom functions listed in STUBS below. Stub semantics come from observed
    behaviour and may differ from the real library in edge cases (ordering,
    error text, null handling). A pass here means "the expression is
    well-formed and handles this data"; it is not proof the real job accepts
    it. Confirm anything non-trivial in a disposable sandbox playbook (see
    dataminr-playbook-builder) or in the Designer.
  * Functions the real library has but this script does not stub fail with
    "Unknown function"; that says nothing about the real job.
  * Test data must include every record shape the job will meet (every
    indicator type, items with and without optional fields, several owners).
    Null-field crashes only appear on the shapes that lack the field.
"""
import json
import re
import sys

try:
    import jmespath
    from jmespath import functions
except ImportError:
    sys.exit("jmespath is not installed. Try: python3 -m venv /tmp/jmv && "
             "/tmp/jmv/bin/pip install jmespath && /tmp/jmv/bin/python " + " ".join(sys.argv))

REF_RE = re.compile(r"#(?:App|Global|Trigger):[^!\s`'\"]+![A-Za-z]+")
ANY = ['string', 'number', 'object', 'array', 'null', 'boolean']

STUBS = ['regex', 'ternary', 'in', 'compact', 'flatten_list', 'group_by', 'include_keys']


class TCStubs(functions.Functions):
    # regex(pattern, value) -> first match (whole match) or null. `.` does not
    # match newlines unless the pattern starts with (?s).
    @functions.signature({'types': ['string']}, {'types': ANY})
    def _func_regex(self, pattern, value):
        text = value if isinstance(value, str) else json.dumps(value)
        m = re.search(pattern, text)
        return m.group(0) if m else None

    # ternary(cond, a, b) -> a if cond is truthy else b (both args evaluated).
    @functions.signature({'types': ANY}, {'types': ANY}, {'types': ANY})
    def _func_ternary(self, cond, a, b):
        return a if cond not in (None, False, '', [], {}) else b

    # in(needle, haystack) -> membership test for array or substring test for string.
    @functions.signature({'types': ANY}, {'types': ['array', 'string', 'null']})
    def _func_in(self, needle, haystack):
        return haystack is not None and needle in haystack

    # compact(array) -> array without null/false/empty values.
    @functions.signature({'types': ['array']})
    def _func_compact(self, arr):
        return [x for x in arr if x not in (None, False, '', [], {})]

    # flatten_list(array of arrays) -> one array (one level).
    @functions.signature({'types': ['array']})
    def _func_flatten_list(self, arr):
        out = []
        for x in arr:
            out.extend(x if isinstance(x, list) else [x])
        return out

    # group_by(array, &expr) -> object keyed by the string of expr, values are
    # arrays of the grouped items (first-seen order). Use values(@) after it.
    @functions.signature({'types': ['array']}, {'types': ['expref']})
    def _func_group_by(self, arr, expref):
        out = {}
        for item in arr:
            key = expref.visit(expref.expression, item)
            out.setdefault(key if isinstance(key, str) else json.dumps(key), []).append(item)
        return out

    # include_keys(object, key, key, ...) -> object restricted to those keys.
    # Raises on a null first argument (observed in the real library).
    @functions.signature({'types': ['object']}, {'types': ['string'], 'variadic': True})
    def _func_include_keys(self, obj, *keys):
        return {k: obj[k] for k in keys if k in obj}


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    subs, head, pos = [], 3000, []
    i = 0
    while i < len(args):
        if args[i] == '--sub':
            subs.append(args[i + 1]); i += 2
        elif args[i] == '--head':
            head = int(args[i + 1]); i += 2
        else:
            pos.append(args[i]); i += 1
    expr = pos[0]
    if expr.startswith('@'):
        try:
            expr = open(expr[1:]).read()
        except OSError as e:
            sys.exit(f"Cannot read expression file {expr[1:]}: {e}")
    expr = expr.strip()
    try:
        data = json.load(open(pos[1]))
    except (OSError, ValueError) as e:
        sys.exit(f"Cannot read sample data {pos[1]}: {e}")

    refs = REF_RE.findall(expr)
    for ref in sorted(set(refs)):
        for s in subs:
            key, _, val = s.partition('=')
            if key in ref:
                expr = expr.replace(ref, val)
                break
    left = sorted(set(REF_RE.findall(expr)))
    if left:
        sys.exit("Unresolved variable references (pass --sub 'name=value' for each):\n  " + "\n  ".join(left))

    used = [f for f in STUBS if re.search(r'\b' + f + r'\(', expr)]
    try:
        result = jmespath.search(expr, data, options=jmespath.Options(custom_functions=TCStubs()))
    except Exception as e:  # noqa: BLE001 - show the engine's message as-is
        print(f"FAILED: {e}")
        print("(This is the standard engine plus stubs; compare with the real job's error text.)")
        sys.exit(2)
    text = json.dumps(result, indent=1, ensure_ascii=False)
    print(text[:head] + ("\n... (truncated)" if len(text) > head else ""))
    n = len(result) if isinstance(result, (list, dict)) else 1
    print(f"\nOK: {len(text)} chars, {n} top-level item(s)")
    if used:
        print("NOTE: used approximate stubs for: " + ", ".join(used) +
              ". Confirm in a sandbox playbook before relying on it.")


if __name__ == '__main__':
    main()
