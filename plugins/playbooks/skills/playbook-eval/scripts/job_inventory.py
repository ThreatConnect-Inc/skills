#!/usr/bin/env python3
"""List the LLM jobs in an exported TIP playbook: model tier, temperature, token cap,
prompt size, tool count, and whether the job is active.

This is step 1 of a model-selection or efficiency review: it shows where models are
used and with what settings, so each job can then be described by the skill it needs.

Usage:
  python3 -I job_inventory.py playbook.json [more.json ...]
  python3 -I job_inventory.py playbook.json --prompts 400   # also print the first N chars of each prompt
  python3 -I job_inventory.py playbook.json --json

Input is the playbook JSON from the v2 export (see playbook-explorer). Read-only.
"""
import argparse, json, sys


def jobs(pb):
    for j in pb.get("jobList", []):
        cfg = j.get("languageModelConfiguration")
        if not cfg:
            continue
        prompts = []
        for p in j.get("jobParameterList", []) or []:
            v = p.get("value") if isinstance(p, dict) else None
            if isinstance(v, str) and len(v) > 200:
                prompts.append(v)
        yield {
            "id": j.get("id"),
            "name": j.get("name"),
            "active": j.get("active", True),
            "model": cfg.get("modelSlug"),
            "temperature": cfg.get("temperature"),
            "maxOutputTokens": cfg.get("maxOutputTokens"),
            "promptChars": sum(len(p) for p in prompts),
            "tools": len(j.get("agentTools") or []) + len(j.get("toolsets") or []),
            "_prompts": prompts,
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--prompts", type=int, metavar="N", help="print the first N chars of each long prompt")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = []
    for f in a.files:
        with open(f) as fh:
            pb = json.load(fh)
        rows = list(jobs(pb))
        out.append({"file": f, "playbook": pb.get("name"), "jobs": [{k: v for k, v in r.items() if k != "_prompts"} for r in rows]})
        if a.json:
            continue
        print(f"\n== {pb.get('name')}  ({f})")
        print("| job | active | model | temp | max tokens | prompt chars | tools |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['name']} | {r['active']} | {r['model']} | {r['temperature']} | {r['maxOutputTokens']} | {r['promptChars']} | {r['tools']} |")
        if a.prompts:
            for r in rows:
                for p in r["_prompts"]:
                    print(f"\n[{r['name']}] {p[:a.prompts]!r}")
    if a.json:
        json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
