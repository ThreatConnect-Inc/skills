#!/usr/bin/env python3
"""Generic retrieval-eval helper (stdlib only). Result files: <dir>/<caseid>__<mode>__r<N>.json holding
{"case": {"id","category","query"}, "mode": "...", "parsed": {"results": [{"id","name","type","score","tags","description"?}]}}.
  pool  <results_dir> <out_prefix> [n_files=4]   unique (case,id) items across modes -> <prefix>1..N.json for blind judges
  score <results_dir> "<labels_glob>" [thr=0.05]  precision@5/10/16 per mode, per-case table, score-band calibration, merge@10
Labels: JSON {"<case>|<id>": {"label": 0|1|2}} (judge pid must be '<case>|<id>'). Control cases (category 'control' or
containing 'non_cyber') are excluded from means. Scoring prints unlabelled counts; fix those before trusting numbers."""
import json, glob, sys, statistics as st, collections

def load(rd):
    R = collections.defaultdict(dict); meta = {}
    for f in sorted(glob.glob(f"{rd}/*__r*.json")):
        d = json.load(open(f))
        if d.get("parsed"): R[d["case"]["id"]][d["mode"]] = d["parsed"]["results"]; meta[d["case"]["id"]] = d["case"]
    return R, meta

def pool(rd, prefix, n=4):
    R, meta = load(rd); items = collections.defaultdict(dict)
    for cid, modes in R.items():
        for rs in modes.values():
            for r in rs: items[cid].setdefault(str(r["id"]), {"type": r.get("type"), "name": r.get("name"), "tags": (r.get("tags") or [])[:8], "description": (r.get("description") or "")[:600]})
    out = [{"case": c, "query": meta[c]["query"], "items": [{"pid": f"{c}|{i}", **v} for i, v in it.items()]} for c, it in items.items()]
    for k in range(n):
        part = out[k::n]; json.dump(part, open(f"{prefix}{k+1}.json", "w"), ensure_ascii=False, indent=1)
        print(f"{prefix}{k+1}.json", sum(len(c['items']) for c in part), "items")

def score(rd, lg, thr=0.05):
    R, meta = load(rd); lab = {}
    for f in glob.glob(lg): lab.update({tuple(k.split("|", 1)): (v["label"] if isinstance(v, dict) else v) for k, v in json.load(open(f)).items()})
    ctl = lambda c: meta[c].get("category") == "control" or "non_cyber" in c
    miss = sum((c, str(r["id"])) not in lab for c, m in R.items() for rs in m.values() for r in rs)
    print("unlabelled items:", miss)
    modes = sorted({m for v in R.values() for m in v})
    def p(c, m, k):
        L = [lab.get((c, str(r["id"]))) for r in R[c][m][:k]]
        return None if not L or None in L else sum(x >= 1 for x in L) / len(L)
    for k in (5, 10, 16):
        print(f"precision@{k}: " + "  ".join(f"{m} {st.mean(v):.2f}" for m in modes for v in [[x for c in R if m in R[c] and not ctl(c) for x in [p(c, m, k)] if x is not None]] if v))
    print(f"{'case':28}" + "".join(f"{m+'@16':>14}" for m in modes))
    for c in sorted(R):
        print(f"{c:28}" + "".join(f"{(('%d/%d' % (round(p(c,m,16)*min(16,len(R[c][m]))), min(16,len(R[c][m])))) if m in R[c] and p(c,m,16) is not None else 'n/a'):>14}" for m in modes))
    if "hybrid" in modes:
        rows = [(r.get("score") or 0, lab[(c, str(r["id"]))]) for c in R if "hybrid" in R[c] and not ctl(c) for r in R[c]["hybrid"] if (c, str(r["id"])) in lab]
        print("score-band calibration (hybrid): " + " | ".join(f"{lo}-{hi}: n={len(b)} rel={sum(l>=1 for _, l in b)/len(b):.2f}" for lo, hi in ((0, .01), (.01, .05), (.05, .2), (.2, 9)) for b in [[x for x in rows if lo <= x[0] < hi]] if b))
    if {"keyword", "hybrid"} <= set(modes):
        a, b = [], []
        for c in R:
            if ctl(c) or not {"keyword", "hybrid"} <= set(R[c]): continue
            ids = list(dict.fromkeys([str(r["id"]) for r in R[c]["hybrid"] if (r.get("score") or 0) >= thr] + [str(r["id"]) for r in R[c]["keyword"]]))[:10]
            kw = [str(r["id"]) for r in R[c]["keyword"]][:10]
            if all((c, i) in lab for i in ids + kw): a.append(sum(lab[(c, i)] >= 1 for i in ids) / len(ids)); b.append(sum(lab[(c, i)] >= 1 for i in kw) / len(kw))
        if a: print(f"merge@10 (hybrid>={thr} first, then keyword) {st.mean(a):.2f} vs keyword@10 {st.mean(b):.2f} (n={len(a)})")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("pool", "score"): sys.exit(__doc__)
    pool(a[1], a[2], int(a[3]) if len(a) > 3 else 4) if a[0] == "pool" else score(a[1], a[2], float(a[3]) if len(a) > 3 else 0.05)
