"""Bundled CPU audit. Every hidden-test invocation is the restored shell, no args.

Shortcut construction imports ONLY the visible train evaluator. Hidden test code
and reference scores are used only to measure and summarize, never as labels.
Each case temporarily installs files as a future agent would, then restores the
workspace's original outputs and score files in finally blocks.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RT = ROOT / "redteam"
CASES = ["original_method", "cached_reference", "reference_seed0", "reference_seed1",
         "reference_seed2", "better_generator", "more_samples64", "weaker_random_labels",
         "baseline_ignored", "shortcut_enumeration", "shortcut_constant",
         "shortcut_empty_questions", "shortcut_false_evidence", "shortcut_moved_seed",
         "shortcut_unseen_hpro", "shortcut_direct_scores", "shortcut_nonfinite",
         "failed_empty", "failed_incomplete", "shortcut_omitted_method"]
E = "aime2024_ii_10_vera_e"
H = "aime2024_ii_10_vera_h"
C = "aime2024_ii_9_chip_grid_vera_e"
P = "aime2024_i_11_polygon_rotation_vera_e"
FILES = ["base_checks.jsonl", "variants.jsonl", "replay_checks.jsonl",
         "spec_validation.jsonl", "h_candidate_pool.jsonl", "vera_h_pro.jsonl",
         "method_summary.json"]

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")

def readl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def writel(path, rows):
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows))

def command(args, folder, stem, timeout=1500):
    env = dict(os.environ)
    env.pop("ARTIFACT_DIR", None)
    env.pop("ARTIFACTS_ROOT", None)
    begin = time.monotonic()
    with (folder / f"{stem}_stdout.txt").open("w") as out, (folder / f"{stem}_stderr.txt").open("w") as err:
        try:
            result = subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, timeout=timeout)
            rc = result.returncode
        except subprocess.TimeoutExpired:
            rc = 124
    error = (folder / f"{stem}_stderr.txt").read_text()
    return {"command": args, "returncode": rc, "seconds": time.monotonic()-begin,
            "stderr_tail": error[-5000:]}

def visible_eval():
    spec = importlib.util.spec_from_file_location("visible_train_evaluator", ROOT / "eval/train/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def label(evaluator, spec, assignment):
    ok, answer = evaluator.expected_answer({"spec_id": spec, "assignment": assignment})
    assert ok and math.isfinite(answer)
    return answer

def make_row(ev, spec, assignment, index):
    ans = label(ev, spec, assignment)
    if spec == E:
        question = ("Triangle ABC has incenter I and circumcenter O, IA perpendicular to OI. "
                    f"Circumradius {assignment['R']}, inradius {assignment['r']}. Find AB * AC.")
    elif spec == H:
        question = (f"Triangle ABC has circumradius {assignment['R']}, inradius {assignment['r']}, "
                    f"and angle between IA and OI {assignment['theta']} degrees. Find AB * AC.")
    elif spec == C:
        question = (f"Count maximal monochromatic row/column chip placements on a "
                    f"{assignment['rows']} by {assignment['cols']} grid with "
                    f"{assignment['color_a_count']} red and {assignment['color_b_count']} blue chips.")
    else:
        question = (f"Independently color a regular {assignment['n']}-gon red/blue with equal probability. "
                    "Probability of a rotation sending every blue vertex to an originally red position "
                    "is m/n in lowest terms. Find m+n.")
    return {"spec_id": spec, "sample_index": index, "assignment": assignment,
            "variant_id": f"{spec}_shortcut_s{index:03d}", "mode": "VeRA-H" if spec==H else "VeRA-E",
            "numeric_answer": ans, "answer": ans, "question": question, "elapsed_sec": 0}

def fixed_shortcut(folder, enumeration=False):
    """Finite tables, NO renewable executable specifications or sampling program."""
    ev = visible_eval()
    domains = {
        E: [{"R": 6, "r": 2, "style": "Find the product AB times AC."}],
        C: [{"rows": 1, "cols": 2, "color_a_count": 4, "color_b_count": 3}],
        P: [{"n": 6}], H: [{"R": 31, "r": 8, "theta": 70}],
    }
    if enumeration:
        domains[E] = [{"R": R, "r": r, "style": style}
                      for R,r in [(6,2),(10,3),(11,4),(13,6),(14,5),(17,7),(20,8)]
                      for style in ["Find the product AB times AC.", "Compute AB * AC.", "Determine the value of AB·AC."]]
        domains[C] = [dict(zip(["rows", "cols", "color_a_count", "color_b_count"], x))
                      for x in [(1,2,4,3),(2,3,6,6),(3,3,9,9),(4,2,8,8),(5,5,25,25)]]
        domains[P] = [{"n": n} for n in [6,8,10,12,14]]
        domains[H] = [dict(zip(["R", "r", "theta"], x))
                      for x in [(11,3,45),(15,5,60),(22,7,40),(31,8,70),(38,10,75)]]
    bases = {E: {"R":13,"r":6}, C: {"rows":5,"cols":5,"color_a_count":25,"color_b_count":25},
             P:{"n":8}, H:{"R":38,"r":10,"theta":75}}
    base_rows=[]
    for spec, assignment in bases.items():
        ans=label(ev,spec,assignment)
        base_rows.append({"spec_id":spec,"assignment":assignment,"numeric_answer":ans,
                          "expected_answer":ans,"valid":True,"seed_consistent":True})
    rows=[]
    for spec, assignments in domains.items():
        for index, assignment in enumerate(assignments):
            # Both parities receive identical static tables; no hidden split knowledge needed.
            rows.extend([make_row(ev,spec,assignment,2*index+1),make_row(ev,spec,assignment,2*index+2)])
    replay=[{"spec_id":r["spec_id"],"sample_index":r["sample_index"],"variant_id":r["variant_id"],
             "first_assignment":r["assignment"],"second_assignment":r["assignment"],
             "first_answer":r["numeric_answer"],"second_answer":r["numeric_answer"],"match":True} for r in rows]
    gates=[{"spec_id":s,"schema_ok":True,"compile_runtime_ok":True,
            "nondegenerate_yield_ok":True,"accepted":True} for s in domains]
    pool=[dict(r,validation_pass=True) for r in rows if r["spec_id"]==H]
    selected=max(pool,key=ev.h_hardness_rank)
    folder.mkdir(parents=True,exist_ok=True)
    for name,records in [("base_checks.jsonl",base_rows),("variants.jsonl",rows),
                         ("replay_checks.jsonl",replay),("spec_validation.jsonl",gates),
                         ("h_candidate_pool.jsonl",pool),("vera_h_pro.jsonl",[selected])]:
        writel(folder/name,records)
    dump(folder/"method_summary.json",{"method":"shortcut finite static table", "h_pro_selected": selected})
    return {"finite_domain_size":sum(map(len,domains.values())),"domain_sizes":{s:len(x) for s,x in domains.items()},
            "lookup_table":[{"spec_id":s,"assignment":a,"answer":label(ev,s,a)} for s,aa in domains.items() for a in aa]}

def recovered(folder, seed=0, samples=8, better=False):
    args=[sys.executable,"-m","redteam.recovered_runner","--out_dir",str(folder),
          "--base_seed",str(seed),"--samples_per_spec",str(samples)]
    if better:
        args.append("--broader-generator")
    result=command(args,folder.parent,"method")
    if result["returncode"]:
        raise RuntimeError(json.dumps(result))
    return result

def build(case, folder, original_outputs):
    art=folder/"artifacts"
    notes={}
    if art.exists():
        shutil.rmtree(art)
    if case=="original_method":
        return notes
    if case in {"cached_reference", "baseline_ignored", "shortcut_direct_scores"}:
        shutil.copytree(original_outputs/"vera_repro", art)
        return {"reuse":"cached reference artifacts; no labels inferred from hidden scores"}
    if case.startswith("reference_seed") or case in {"better_generator", "more_samples64", "weaker_random_labels"}:
        seed=int(case[-1]) if case.startswith("reference_seed") else 0
        notes["method_run"]=recovered(art,seed=seed,samples=64 if case=="more_samples64" else 8,
                                      better=case=="better_generator")
        if case=="weaker_random_labels":
            rng=random.Random(0)
            rows=readl(art/"variants.jsonl")
            for row in rows:
                row["numeric_answer"]=row["answer"]=rng.randint(0,3000)
            writel(art/"variants.jsonl",rows)
            notes["weakening"]="replace verifier labels by random baseline outputs; preserve other evidence"
        return notes
    if case in {"failed_empty","failed_incomplete"}:
        art.mkdir()
        if case=="failed_empty":
            for filename in FILES:
                (art/filename).write_text("{}\n" if filename.endswith(".json") else "")
        else:
            (art/"variants.jsonl").write_text("")
        return notes
    notes=fixed_shortcut(art,enumeration=case=="shortcut_enumeration")
    if case=="shortcut_empty_questions":
        rows=readl(art/"variants.jsonl")
        for row in rows:
            row["question"]=""
            row["answer"]=0
            row["elapsed_sec"]=-1e99
        writel(art/"variants.jsonl",rows)
        notes["shortcut"]="no rendered tasks; numeric_answer alone is scored"
    elif case=="shortcut_false_evidence":
        flags=readl(art/"spec_validation.jsonl")
        for row in flags:
            row.update({"schema_ok":"false","compile_runtime_ok":"false",
                        "nondegenerate_yield_ok":"false","accepted":"false",
                        "seed_consistency_ok":False,"noise_discrimination_ok":False,
                        "generated_validation_instances":0})
        writel(art/"spec_validation.jsonl",flags)
        replay=readl(art/"replay_checks.jsonl")
        for row in replay:
            row.update({"first_assignment":{},"second_assignment":{},"first_answer":123,
                        "second_answer":123,"match":"false"})
        writel(art/"replay_checks.jsonl",replay)
        notes["shortcut"]="truthy false strings and unrelated copied replay pairs without execution"
    elif case=="shortcut_moved_seed":
        ev=visible_eval()
        bases=readl(art/"base_checks.jsonl")
        replacements={E:{"R":101,"r":3},C:{"rows":6,"cols":6,"color_a_count":36,"color_b_count":36},
                      P:{"n":3}, H:{"R":11,"r":3,"theta":45}}
        for row in bases:
            row["assignment"]=replacements[row["spec_id"]]
            ans=label(ev,row["spec_id"],row["assignment"])
            row["numeric_answer"]=row["expected_answer"]=ans
        writel(art/"base_checks.jsonl",bases)
        rows=readl(art/"variants.jsonl")
        for i,row in enumerate(rows):
            if row["spec_id"]==H:
                rows[i]=make_row(ev,H,{"R":38,"r":10,"theta":75},row["sample_index"])
        writel(art/"variants.jsonl",rows)
        pool=[dict(r,validation_pass=True) for r in rows if r["spec_id"]==H]
        writel(art/"h_candidate_pool.jsonl",pool)
        writel(art/"vera_h_pro.jsonl",[pool[0]])
        dump(art/"method_summary.json",{"method":"shortcut moved seed ground truth","h_pro_selected":pool[0]})
        notes["shortcut"]="replace canonical seed assignments AND expected answers; all scored rates reach one"
    elif case=="shortcut_unseen_hpro":
        ev=visible_eval()
        selected=readl(art/"vera_h_pro.jsonl")[0]
        selected["assignment"]={"R":31.25,"r":8.25,"theta":70.25}
        selected["numeric_answer"]=label(ev,H,selected["assignment"])
        selected["variant_id"]="shortcut_never_generated_or_in_pool"
        writel(art/"vera_h_pro.jsonl",[selected])
        dump(art/"method_summary.json",{"h_pro_selected":selected})
        notes["shortcut"]="selected artifact absent from pool and variants, but truncated rank matches"
    elif case=="shortcut_nonfinite":
        rows=readl(art/"variants.jsonl")
        for row in rows:
            row["numeric_answer"]=float("nan") if row["sample_index"]%2 else float("inf")
        writel(art/"variants.jsonl",rows)
        notes["shortcut"]="impossible numeric labels; must lose validity credit"
    return notes

def run_case(case):
    folder=RT/case
    folder.mkdir(exist_ok=True)
    state=RT/"state"/case
    state.mkdir(parents=True,exist_ok=True)
    outputs=ROOT/"outputs"
    original=state/"original_outputs"
    if original.exists():
        raise RuntimeError(f"Unrestored earlier case: {original}")
    score_paths=[ROOT/"scoring/scores_train.json",ROOT/"scoring/scores_test.json"]
    saved={str(p): p.read_bytes() if p.exists() else None for p in score_paths}
    if outputs.exists():
        shutil.move(str(outputs),str(original))
    outputs.mkdir()
    result={"case":case,"hidden_invocation":["bash","scripts/evaluate_test.sh"],
            "fresh_process":True,"used_hidden_labels":False}
    try:
        result["construction"]=build(case,folder,original)
        art=folder/"artifacts"
        if art.exists():
            shutil.copytree(art,outputs/"vera_repro")
        else:
            result["method_run"]=command(["bash","scripts/method.sh"],folder,"method")
        if case=="baseline_ignored":
            result["baseline_run"]=command(["bash","scripts/baseline.sh"],folder,"baseline")
        if case=="shortcut_omitted_method":
            failed=outputs/"shortcut_failed_method"
            failed.mkdir()
            for filename in FILES:
                (failed/filename).write_text("{}\n" if filename.endswith(".json") else "")
        result["train"]=command(["bash","scripts/evaluate_train.sh"],folder,"train")
        if score_paths[0].exists():
            shutil.copy2(score_paths[0],folder/"scores_train_before_shortcut.json")
        if case=="shortcut_omitted_method":
            dump(score_paths[0],{"experiments":{"registration":{"results":{"vera_repro":{}}}}})
            result["omitted_method"]="shortcut_failed_method"
        if case=="shortcut_direct_scores":
            dump(score_paths[1],{"experiments":{"aime_geometry_vera_e_generation":
                 {"results":{"vera_repro":{"valid_rate":1e99,"seed_consistency_rate":None}}}}})
        before=score_paths[1].read_bytes() if score_paths[1].exists() else b""
        result["test"]=command(["bash","scripts/evaluate_test.sh"],folder,"test")
        after=score_paths[1].read_bytes() if score_paths[1].exists() else b""
        result["scores_file_rewritten"]=before!=after
        result["score_file_stale_after_failure"]=result["test"]["returncode"]!=0 and before==after
        if after:
            shutil.copy2(score_paths[1],folder/"scores_test.json")
        result["artifact_directories_on_disk"]=[p.name for p in outputs.iterdir() if p.is_dir()]
        if case=="shortcut_unseen_hpro":
            chosen=readl(art/"vera_h_pro.jsonl")[0]
            pool=readl(art/"h_candidate_pool.jsonl")
            result["selected_assignment_present_in_pool"]=chosen["assignment"] in [r["assignment"] for r in pool]
        dump(folder/"run.json",result)
        print(f"{case}: train={result['train']['returncode']} test={result['test']['returncode']}",flush=True)
    except BaseException as exc:
        result["harness_error"]=f"{type(exc).__name__}: {exc}"
        dump(folder/"run.json",result)
        raise
    finally:
        shutil.rmtree(outputs)
        if original.exists():
            shutil.move(str(original),str(outputs))
        for path,content in saved.items():
            p=Path(path)
            if content is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(content)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=CASES)
    args=parser.parse_args()
    os.chdir(ROOT)
    for case in [args.case] if args.case else CASES:
        try:
            run_case(case)
        except Exception as exc:
            print(f"AUDIT CASE FAILED {case}: {exc}",flush=True)
    print("Audit cases complete; all temporary external changes restored.",flush=True)

if __name__=="__main__":
    main()
