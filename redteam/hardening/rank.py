"""Rank every scored method against the reference with scoring/reference.json.

rank(m) = sum_exp weight_exp * sum_metric |coef| * dir * (v_m - v_ref) / sd_metric

where dir = +1 if higher_is_better else -1 and sd_metric is the population
standard deviation of that metric across the methods in the scores file (the
cohort of attempts being ranked; metrics with zero spread are skipped).  The
raw delta drops the division by sd.  A method missing from an experiment
contributes nothing for that experiment.

Usage: python redteam/hardening/rank.py scores_test.json [--reference vera_e] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rank(scores: dict, ref_method: str, reference: dict) -> dict:
    exps = reference["experiments"]
    out: dict = {}
    methods = sorted({m for e in scores["experiments"].values() for m in e["results"]})
    for m in methods:
        raw = norm = 0.0
        for exp, spec in exps.items():
            res = scores["experiments"].get(exp, {}).get("results", {})
            if m not in res or ref_method not in res:
                continue
            for metric, mdef in spec["metrics"].items():
                c = abs(mdef["coefficient"])
                if c == 0:
                    continue
                if metric not in res[m] or metric not in res[ref_method]:
                    continue  # e.g. a metric the pre-hardening evaluator did not report
                vals = [r[metric] for r in res.values() if metric in r]
                sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
                d = (1 if mdef["higher_is_better"] else -1) * (res[m][metric] - res[ref_method][metric])
                raw += spec["weight"] * c * d
                if sd > 0:
                    norm += spec["weight"] * c * d / sd
        out[m] = {"raw_delta": round(raw, 5), "normalized_delta": round(norm, 5)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("scores", nargs="+")
    ap.add_argument("--reference", default="vera_e")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    reference = json.loads((ROOT / "scoring/reference.json").read_text())
    report = {}
    for path in args.scores:
        scores = json.loads(Path(path).read_text())
        table = rank(scores, args.reference, reference)
        report[path] = {"ranks": table, "metrics": {
            exp: {m: {k: round(v, 4) for k, v in r.items()} for m, r in e["results"].items()}
            for exp, e in scores["experiments"].items()},
            "status": {m: s.get("status") for m, s in scores.get("_meta", {}).get("methods", {}).items()}}
        print(f"== {path} (reference {args.reference})")
        for m, r in sorted(table.items(), key=lambda kv: -kv[1]["normalized_delta"]):
            st = report[path]["status"].get(m, "?")
            vals = " ".join(f"{exp.split('_')[-1]}:y={e['results'][m]['verified_fresh_yield']:.3f},"
                            f"c={e['results'][m]['certified_spec_rate']:.3f},"
                            f"w={e['results'][m].get('mislabeled_spec_rate', float('nan')):.3f},"
                            f"p={e['results'][m]['label_precision']:.3f}"
                            for exp, e in scores["experiments"].items() if m in e["results"])
            print(f"  {m:28s} {st:6s} raw={r['raw_delta']:+.4f} norm={r['normalized_delta']:+.3f}  {vals}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
