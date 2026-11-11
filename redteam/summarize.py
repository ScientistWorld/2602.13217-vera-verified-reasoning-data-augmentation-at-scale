"""Summarize actual hidden-test writes, with explicitly audit-dependent scaling."""
from __future__ import annotations
import json
import math
from pathlib import Path
from statistics import mean, pstdev

RT=Path(__file__).resolve().parent
CONFIG=json.loads((RT/"reference_config.json").read_text())["experiments"]
REF=json.loads((RT/"reference_scores_test.json").read_text())["experiments"]

def get(data,e,m,method="vera_repro"):
    value=data.get("experiments",{}).get(e,{}).get("results",{}).get(method,{}).get(m)
    return value if isinstance(value,(int,float)) and math.isfinite(value) else None

def main():
    cases={}
    for path in sorted(RT.glob("*/run.json")):
        run=json.loads(path.read_text())
        scores_path=path.parent/"scores_test.json"
        scores=json.loads(scores_path.read_text()) if scores_path.exists() else {}
        cases[path.parent.name]={"run":run,"scores":scores}
    successful={n:d for n,d in cases.items() if d["run"].get("test",{}).get("returncode")==0}
    scales={}
    for e,exp in CONFIG.items():
        scales[e]={}
        for m,cfg in exp["metrics"].items():
            vals=[get(d["scores"],e,m) for d in successful.values()]
            vals=[v for v in vals if v is not None]
            scales[e][m]=pstdev(vals) if len(vals)>1 else 0
    summary={"reference_source":"audit-start scoring/scores_test.json",
             "coefficient_source":"scoring/reference.json, absolute coefficients",
             "normalization":"population std across successful audit cases listed below; NOT a fixed future rank",
             "normalization_cohort":sorted(successful),"metric_std":scales,"cases":{}}
    for name,data in cases.items():
        run=data["run"]
        entry={"test_returncode":run.get("test",{}).get("returncode"),
               "score_file_stale_after_failure":run.get("score_file_stale_after_failure"),
               "raw_weighted_delta":None,"audit_normalized_delta":None}
        if name in successful:
            raw=normalized=0.0
            missing=[]
            for e,exp in CONFIG.items():
                for m,cfg in exp["metrics"].items():
                    coef=abs(cfg["coefficient"])*exp.get("weight",1)
                    if not coef:
                        continue
                    val=get(data["scores"],e,m)
                    ref=get({"experiments":REF},e,m)
                    if val is None or ref is None:
                        missing.append(f"{e}.{m}")
                        continue
                    difference=(val-ref)*(1 if cfg["higher_is_better"] else -1)
                    raw+=coef*difference
                    std=scales[e][m]
                    if std:
                        normalized+=coef*difference/std
            entry.update(raw_weighted_delta=raw,audit_normalized_delta=normalized,missing_metrics=missing)
            entry["metrics"]={e:v["results"].get("vera_repro",{}) for e,v in data["scores"].get("experiments",{}).items()}
            entry["methods_written"]=sorted({m for exp in data["scores"].get("experiments",{}).values() for m in exp.get("results",{})})
            if name=="shortcut_omitted_method":
                entry["omitted_method_rank_delta_under_skip_missing_rule"]=0
        art=RT/name/"artifacts/variants.jsonl"
        if art.exists():
            rows=[json.loads(line) for line in art.read_text().splitlines() if line]
            entry["artifact_stats"]={}
            for spec in sorted({r["spec_id"] for r in rows}):
                rr=[r for r in rows if r["spec_id"]==spec]
                numeric_keys={"R","r","theta","rows","cols","color_a_count","color_b_count","n"}
                semantic={json.dumps({k:v for k,v in r["assignment"].items() if k in numeric_keys},sort_keys=True) for r in rr}
                entry["artifact_stats"][spec]={"row_count":len(rr),"distinct_numeric_assignments":len(semantic)}
        summary["cases"][name]=entry
    seeds=[summary["cases"].get(f"reference_seed{s}",{}) for s in range(3)]
    summary["recovered_seed_spread"]={}
    for key in ["raw_weighted_delta","audit_normalized_delta"]:
        vals=[x.get(key) for x in seeds]
        if all(v is not None for v in vals):
            summary["recovered_seed_spread"][key]={"values":vals,"range":max(vals)-min(vals),"population_std":pstdev(vals)}
    summary["per_metric_recovered_seed_range"]={}
    for e,exp in CONFIG.items():
        summary["per_metric_recovered_seed_range"][e]={}
        for m,cfg in exp["metrics"].items():
            vals=[x.get("metrics",{}).get(e,{}).get(m) for x in seeds]
            if all(v is not None for v in vals):
                summary["per_metric_recovered_seed_range"][e][m]={"values":vals,"range":max(vals)-min(vals)}
    summary["reference_at_upper_bound"]={e:[m for m,cfg in exp["metrics"].items()
        if abs(cfg["coefficient"])>0 and get({"experiments":REF},e,m)==1] for e,exp in CONFIG.items()}
    (RT/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    lines=["case\traw_delta\taudit_normalized_delta\ttest_returncode"]
    for name,entry in summary["cases"].items():
        lines.append(f"{name}\t{entry['raw_weighted_delta']}\t{entry['audit_normalized_delta']}\t{entry['test_returncode']}")
    (RT/"summary.tsv").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))

if __name__=="__main__":
    main()
