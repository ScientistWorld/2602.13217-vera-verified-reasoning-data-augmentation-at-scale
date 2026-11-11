"""Hidden-test evaluator for GSM8K VeRA-E executable specifications.

Scores every method directory under outputs/ (each immediate subdirectory is
one method).  A method submits ``outputs/<method>/specs.jsonl`` with one
executable specification per seed:

    {"seed_id": ..., "template": "... {n0} ... {n1} ...",
     "generator_code": "def generator(rng): ...",
     "verifier_code": "def verifier(assign): ... return valid, answer"}

Nothing else the method writes is read.  For every hidden test seed the
evaluator itself executes the submitted code in a sandboxed subprocess on
secret RNG keys, then recomputes every label with the seed's hidden reference
program (eval/test/references.jsonl).  Scores are computed from those raw
executions only.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import hashlib
import json
import math
import os
import string
import subprocess
import sys
from pathlib import Path

SLICE = "test"
HERE = Path(__file__).resolve().parent
REFERENCES = HERE / "references.jsonl"
RUNNER = HERE / "sandbox_runner.py"
KEY_SALT = "vera-e-hidden-test-7f3c91d2a85e4b6f"
K_SAMPLES = 8
MAX_CODE_CHARS = 20000
MAX_TEMPLATE_CHARS = 4000
MAX_SLOT_VALUE = 1e9
PRECISION_FLOOR = 0.8  # pooled fresh-label precision below this is a failed run
WALL_SECONDS = 90
EXPERIMENTS = {
    "gsm8k_vera_e_core": lambda ref: ref["n_steps"] <= 3,
    "gsm8k_vera_e_multistep": lambda ref: ref["n_steps"] >= 4,
}
METRICS = ["verified_fresh_yield", "label_precision", "certified_spec_rate", "seed_consistency_rate"]
WORST = {m: 0.0 for m in METRICS}
ALLOWED_IMPORTS = {"math", "random", "fractions", "itertools", "functools"}
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "getattr", "setattr", "delattr", "globals",
    "locals", "vars", "input", "breakpoint", "memoryview", "type", "object", "super",
    "classmethod", "staticmethod", "property", "help", "dir", "id", "hash",
}
FORBIDDEN_ATTRS = {
    "gi_frame", "gi_code", "gi_yieldfrom", "gi_running", "cr_frame", "cr_code", "cr_await",
    "ag_frame", "ag_code", "f_back", "f_globals", "f_builtins", "f_locals", "f_code", "f_trace",
    "tb_frame", "tb_next", "co_code", "co_consts", "mro", "format_map", "with_traceback",
}


# ----------------------------------------------------------------------------
# Reference programs
# ----------------------------------------------------------------------------

def _eval_node(node: ast.AST, env: dict) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        return float(env[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, env)
    if isinstance(node, ast.BinOp):
        a = _eval_node(node.left, env)
        b = _eval_node(node.right, env)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            if b == 0:
                raise ZeroDivisionError
            return a / b
    raise ValueError("unsupported reference node")


def reference_label(ref: dict, assign: dict) -> tuple[bool, int | None]:
    """Validity rule: no division by zero, every intermediate >= 0, and a
    non-negative integer final answer (as every seed answer is)."""
    env = dict(assign)
    try:
        value = 0.0
        for j, step in enumerate(ref["_compiled"]):
            value = _eval_node(step, env)
            if not math.isfinite(value) or value < -1e-9:
                return False, None
            env[f"r{j}"] = value
    except (ZeroDivisionError, OverflowError, ValueError, KeyError):
        return False, None
    if abs(value - round(value)) > 1e-6 * max(1.0, abs(value)) or value < -1e-9:
        return False, None
    return True, int(round(value))


def load_references() -> list[dict]:
    refs = []
    with REFERENCES.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ref = json.loads(line)
                ref["_compiled"] = [ast.parse(s, mode="eval") for s in ref["steps"]]
                refs.append(ref)
    return refs


# ----------------------------------------------------------------------------
# Static checks on submitted specs
# ----------------------------------------------------------------------------

def static_problem(spec: dict, slot_names: list[str]) -> str | None:
    for field in ("template", "generator_code", "verifier_code"):
        if not isinstance(spec.get(field), str):
            return f"missing_{field}"
    if len(spec["template"]) > MAX_TEMPLATE_CHARS:
        return "template_too_long"
    for field in ("generator_code", "verifier_code"):
        code = spec[field]
        if len(code) > MAX_CODE_CHARS:
            return f"{field}_too_long"
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return f"{field}_syntax"
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in FORBIDDEN_ATTRS):
                return "private_attribute"
            if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in FORBIDDEN_NAMES):
                return "forbidden_name"
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("__"):
                return "dunder_def"
            if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Await, ast.Global, ast.Nonlocal)):
                return "forbidden_construct"
            if isinstance(node, ast.Import):
                if any(a.name not in ALLOWED_IMPORTS for a in node.names):
                    return "forbidden_import"
            if isinstance(node, ast.ImportFrom):
                if node.level or node.module not in ALLOWED_IMPORTS:
                    return "forbidden_import"
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
                return "dunder_string"
    try:
        fields = [f for _, f, _, _ in string.Formatter().parse(spec["template"]) if f is not None]
    except ValueError:
        return "template_format"
    if set(fields) != set(slot_names) or any(not f.isidentifier() for f in fields):
        return "template_fields"
    return None


# ----------------------------------------------------------------------------
# Execution and per-seed scoring
# ----------------------------------------------------------------------------

def sample_keys(seed_id: str) -> list[int]:
    return [int(hashlib.sha256(f"{KEY_SALT}|{seed_id}|{k}".encode()).hexdigest()[:15], 16) for k in range(K_SAMPLES)]


def run_sandbox(spec: dict, ref: dict) -> dict:
    request = {
        "generator_code": spec["generator_code"],
        "verifier_code": spec["verifier_code"],
        "seed_assignment": ref["seed_assignment"],
        "keys": sample_keys(ref["seed_id"]),
    }
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0"}
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-S", str(RUNNER)],
            input=json.dumps(request), capture_output=True, text=True,
            timeout=WALL_SECONDS, cwd="/", env=env,
        )
        return json.loads(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"sandbox:{type(exc).__name__}", "samples": []}


def normalize_assign(assign, ref: dict):
    if not isinstance(assign, dict) or set(assign) != set(ref["slot_kinds"]):
        return None
    out = {}
    for name, kind in ref["slot_kinds"].items():
        v = assign[name]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        v = float(v)
        if not math.isfinite(v) or v <= 0 or v > MAX_SLOT_VALUE:
            return None
        if kind == "int":
            if abs(v - round(v)) > 1e-9:
                return None
            out[name] = int(round(v))
        else:
            out[name] = v
    return out


def value_strings(v) -> set[str]:
    if isinstance(v, int):
        return {str(v), f"{v:,}"}
    s = {repr(v), f"{v:g}", f"{v:.2f}".rstrip("0").rstrip(".")}
    if float(v).is_integer():
        s.add(str(int(v)))
    return s


def renders(template: str, assign: dict, min_len: int) -> bool:
    try:
        text = template.format(**{k: (v if isinstance(v, int) else (int(v) if float(v).is_integer() else v)) for k, v in assign.items()})
    except Exception:  # noqa: BLE001
        return False
    if len(text) < min_len:
        return False
    return all(any(s in text for s in value_strings(v)) for v in assign.values())


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


def score_seed(spec: dict | None, ref: dict, question_len: int) -> dict:
    res = {"seed_consistent": False, "certified": False, "yield": 0.0, "accepted_fresh": 0, "correct_fresh": 0}
    if spec is None:
        res["error"] = "no_spec"
        return res
    problem = static_problem(spec, list(ref["slot_kinds"]))
    if problem:
        res["error"] = problem
        return res
    out = run_sandbox(spec, ref)
    if not out.get("ok"):
        res["error"] = out.get("error", "sandbox_failed")
        return res
    seed_v = out.get("seed") or {}
    res["seed_consistent"] = (
        seed_v.get("valid") is True
        and isinstance(seed_v.get("label"), (int, float))
        and not isinstance(seed_v.get("label"), bool)
        and close(seed_v["label"], ref["answer"])
    )
    seed_key = tuple(ref["seed_assignment"][k] for k in ref["slot_kinds"])
    counted = set()
    wrong = 0
    min_len = int(0.25 * question_len)
    for sample in out.get("samples", [])[:K_SAMPLES]:
        raw = sample.get("assign")
        verdict = sample.get("verdict") or {}
        accepted = verdict.get("valid") is True
        assign = normalize_assign(raw, ref)
        key = tuple(assign[k] for k in ref["slot_kinds"]) if assign else None
        fresh = key is not None and key != seed_key
        if raw is not None and accepted and (key is None or fresh):
            res["accepted_fresh"] += 1
        if not accepted:
            continue
        label = verdict.get("label")
        if assign is None:
            wrong += 1
            continue
        if not fresh:
            continue
        ref_ok, ref_label = reference_label(ref, assign)
        label_ok = isinstance(label, (int, float)) and not isinstance(label, bool) and ref_ok and close(label, ref_label)
        if not label_ok:
            wrong += 1
            continue
        res["correct_fresh"] += 1
        replay = normalize_assign(sample.get("replay"), ref)
        if replay != assign:
            continue
        if not renders(spec["template"], assign, min_len):
            continue
        counted.add(key)
    res["wrong_fresh"] = wrong
    # A seed counts as seed-consistent only if its spec is also renewable
    # (it certifies at least one fresh variant); replaying the seed alone is not.
    res["seed_consistent"] = bool(res["seed_consistent"] and res["accepted_fresh"] >= 1)
    res["certified"] = bool(res["seed_consistent"] and wrong == 0 and counted)
    res["yield"] = len(counted) / K_SAMPLES if res["certified"] else 0.0
    return res


# ----------------------------------------------------------------------------
# Method discovery and aggregation
# ----------------------------------------------------------------------------

def load_specs(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "missing specs.jsonl"
    specs: dict[str, dict] = {}
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("seed_id"), str):
                    return None, "malformed row"
                if row["seed_id"] in specs:
                    return None, f"duplicate seed_id {row['seed_id']}"
                specs[row["seed_id"]] = row
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"unreadable specs.jsonl ({type(exc).__name__})"
    return specs, None


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    acc = sum(r["accepted_fresh"] for r in rows)
    cor = sum(r["correct_fresh"] for r in rows)
    return {
        "verified_fresh_yield": sum(r["yield"] for r in rows) / n,
        "label_precision": cor / acc if acc else 0.0,
        "certified_spec_rate": sum(r["certified"] for r in rows) / n,
        "seed_consistency_rate": sum(r["seed_consistent"] for r in rows) / n,
    }


def score_method(method_dir: Path, refs: list[dict], questions: dict) -> tuple[dict, dict]:
    specs, problem = load_specs(method_dir / "specs.jsonl")
    if specs is None:
        return {exp: dict(WORST) for exp in EXPERIMENTS}, {"status": "failed", "reason": problem}
    with cf.ThreadPoolExecutor(max_workers=max(1, min(16, os.cpu_count() or 1))) as pool:
        per_seed = list(pool.map(lambda r: score_seed(specs.get(r["seed_id"]), r, questions.get(r["seed_id"], 0)), refs))
    by_id = {r["seed_id"]: row for r, row in zip(refs, per_seed)}
    overall = aggregate(per_seed)
    status = {"status": "ok", "overall": overall,
              "errors": {}}
    for row in per_seed:
        if row.get("error"):
            status["errors"][row["error"]] = status["errors"].get(row["error"], 0) + 1
    if overall["label_precision"] < PRECISION_FLOOR:
        status.update(status="failed", reason=f"label precision {overall['label_precision']:.3f} < {PRECISION_FLOOR}")
        return {exp: dict(WORST) for exp in EXPERIMENTS}, status
    results = {}
    for exp, member in EXPERIMENTS.items():
        rows = [by_id[r["seed_id"]] for r in refs if member(r)]
        results[exp] = aggregate(rows)
    return results, status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", default="outputs")
    ap.add_argument("--seeds", default="data/gsm8k_vera/test_seeds.jsonl")
    ap.add_argument("--scores", default="scoring/scores_test.json")
    args = ap.parse_args()

    refs = load_references()
    questions = {}
    seeds_path = Path(args.seeds)
    if seeds_path.is_file():
        for line in seeds_path.open(encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                questions[row["seed_id"]] = len(row["question"])
    root = Path(args.outputs)
    methods = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))) if root.is_dir() else []

    scores: dict = {"slice": SLICE, "experiments": {exp: {"results": {}} for exp in EXPERIMENTS}, "_meta": {
        "k_samples": K_SAMPLES, "n_seeds": {exp: sum(1 for r in refs if m(r)) for exp, m in EXPERIMENTS.items()},
        "methods": {}}}
    for method_dir in methods:
        results, status = score_method(method_dir, refs, questions)
        for exp, metrics in results.items():
            scores["experiments"][exp]["results"][method_dir.name] = metrics
        scores["_meta"]["methods"][method_dir.name] = status
        print(f"[{SLICE}] {method_dir.name}: {status['status']} {json.dumps(results)}", flush=True)

    out = Path(args.scores)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
