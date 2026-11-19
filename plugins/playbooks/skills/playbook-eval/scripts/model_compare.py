#!/usr/bin/env python3
"""Compare models on benchmark numbers you supply (no network access).

Gather the numbers yourself from sources whose terms allow your use (provider model
cards, papers, evaluation reports you ran, or a leaderboard you may copy from by hand),
and save them as CSV or JSON. This script only formats and compares them.

Input
  CSV : first column is the model name, the other columns are scores or prices
        model,intelligence,gdpval_elo,price_in,price_out
        small,41,900,0.25,1.25
  JSON: a list of objects with a "model" key, or {"model name": {"score": value, ...}}

Usage (stdlib only; run with -I because the input is data, not code)
  python3 -I model_compare.py --file models.csv
  python3 -I model_compare.py --file models.csv --scores intelligence,gdpval_elo --sort intelligence
  python3 -I model_compare.py --file models.csv --winprob gdpval_elo
  python3 -I model_compare.py --file models.json --json

Missing values print as "-" and mean "not available", never zero.
"""
import argparse, csv, json, sys


def load(path):
    with open(path, encoding="utf-8") as f:
        if path.lower().endswith(".json"):
            data = json.load(f)
            if isinstance(data, dict):
                data = [dict(model=k, **v) for k, v in data.items()]
            return data
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v):
    n = num(v)
    if n is None:
        return "-" if v in (None, "") else str(v)
    return f"{n:.0f}" if n == int(n) and abs(n) >= 100 else f"{n:.3g}"


def win_prob(a, b):
    """Expected win rate of Elo rating a over b."""
    return 1 / (1 + 10 ** ((b - a) / 400))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="CSV or JSON of model scores")
    ap.add_argument("--scores", help="comma-separated columns to show (default: all)")
    ap.add_argument("--sort", help="column to sort by, descending")
    ap.add_argument("--winprob", metavar="ELO_COLUMN", help="print pairwise win probability for an Elo column")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    a = ap.parse_args()

    rows = load(a.file)
    if not rows:
        sys.exit("no rows in input")
    keys = [k for k in rows[0].keys() if k != "model"]
    cols = a.scores.split(",") if a.scores else keys
    if a.sort:
        rows.sort(key=lambda r: (num(r.get(a.sort)) is None, -(num(r.get(a.sort)) or 0)))
    if a.json:
        print(json.dumps([{c: r.get(c) for c in ["model"] + cols} for r in rows], indent=2))
    else:
        print("| model | " + " | ".join(cols) + " |")
        print("|---|" + "---|" * len(cols))
        for r in rows:
            print(f"| {r['model']} | " + " | ".join(fmt(r.get(c)) for c in cols) + " |")
    if a.winprob:
        elo = {r["model"]: num(r.get(a.winprob)) for r in rows if num(r.get(a.winprob)) is not None}
        print(f"\nExpected win rate of row over column ({a.winprob}):\n")
        names = list(elo)
        print("| vs | " + " | ".join(names) + " |")
        print("|---|" + "---|" * len(names))
        for x in names:
            print(f"| {x} | " + " | ".join("-" if x == y else f"{win_prob(elo[x], elo[y]):.0%}" for y in names) + " |")


if __name__ == "__main__":
    main()
