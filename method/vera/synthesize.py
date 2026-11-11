"""VeRA-E human-free synthesis loop (paper Sec. 3.3-3.4, Algorithm 1).

For every seed (question, answer, slot schema) a Teacher LLM proposes an
executable specification (template, generator, verifier).  Each candidate goes
through the paper's validation gates:

  (1) schema parse, (2) sandbox compilation, (3) runtime on a batch of
  hash-seeded samples, (4) non-degenerate yield, and (5) VeRA-E seed-anchored
  consistency  V(theta_seed) == (True, a).

Failures are turned into structured feedback and the Teacher retries (default
cap 20 attempts per seed, Table 1).  Accepted specifications are packaged with
the paper's sampler semantics (generator retried until the verifier accepts)
and written to outputs/<variant>/specs.jsonl.

Variants written by one run (they share the Teacher calls):
  vera_e         paper gates, up to --max_attempts attempts (reference)
  vera_e_1try    the same pipeline restricted to the first attempt (Table 1 "1 try")
  vera_e_seed1   the reference pipeline with a different retry sampling seed
                 (measures run-to-run noise of the reference)
  vera_e_xcheck  paper gates + a randomized cross-check gate (Sec. 5.2:
                 "spec-level tests ... randomized fuzzing"): the verifier must not
                 ignore any slot, and must agree with an independently derived
                 solve() program on fresh generator samples.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import os
import re
import time
from collections import Counter
from pathlib import Path

from . import prompts, sandbox

N_VALIDATION = 20
MIN_YIELD = 0.25


# ----------------------------------------------------------------------------
# Parsing Teacher output
# ----------------------------------------------------------------------------

def parse_spec(text: str) -> tuple[dict | None, str | None]:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```\s*$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None, "Output did not contain a JSON object."
    try:
        obj = json.loads(t[i:j + 1], strict=False)
    except json.JSONDecodeError as exc:
        return None, f"Output was not valid JSON ({exc.msg} at char {exc.pos}). Escape newlines in code strings as \\n."
    if not isinstance(obj, dict):
        return None, "Output JSON must be an object."
    spec = {}
    for key in ("template", "generator", "verifier"):
        val = obj.get(key)
        if isinstance(val, dict):
            val = val.get("code")
        if not isinstance(val, str) or not val.strip():
            return None, f"Missing required string field '{key}'."
        spec[key] = val
    return spec, None


def parse_solve(text: str) -> str | None:
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    code = m.group(1) if m else text
    return code if "def solve" in code else None


# ----------------------------------------------------------------------------
# Packaging: the paper's sampler (retry generator until verifier accepts)
# ----------------------------------------------------------------------------

def rename(code: str) -> str:
    code = re.sub(r"\bdef\s+generator\s*\(", "def teacher_generator(", code)
    code = re.sub(r"\bdef\s+verifier\s*\(", "def teacher_verifier(", code)
    code = re.sub(r"(?<![\w.])generator\s*\(", "teacher_generator(", code)
    code = re.sub(r"(?<![\w.])verifier\s*\(", "teacher_verifier(", code)
    code = code.replace("def teacher_teacher_", "def teacher_").replace("teacher_teacher_", "teacher_")
    return code


def package(spec: dict, seed: dict) -> dict:
    names = [s["name"] for s in seed["slots"]]
    ints = [s["name"] for s in seed["slots"] if s["kind"] == "int"]
    teacher = rename(spec["generator"]) + "\n\n" + rename(spec["verifier"]) + "\n"
    verifier = f'''
def verifier(assign):
    names = {names!r}
    if not isinstance(assign, dict) or sorted(assign) != sorted(names):
        return False, None
    for k in names:
        v = assign[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v <= 0:
            return False, None
        if k in {ints!r} and v != int(v):
            return False, None
    try:
        res = teacher_verifier(dict(assign))
    except Exception:
        return False, None
    if not isinstance(res, (tuple, list)) or len(res) != 2 or res[0] is not True:
        return False, None
    y = res[1]
    if isinstance(y, bool) or not isinstance(y, (int, float)) or y != y or y < 0 or abs(y - round(y)) > 1e-6:
        return False, None
    return True, int(round(y))
'''
    generator = '''
def generator(rng):
    a = None
    for attempt in range(64):
        try:
            a = teacher_generator(rng)
        except Exception:
            continue
        if verifier(a)[0]:
            return a
    return a
'''
    return {
        "seed_id": seed["seed_id"],
        "template": spec["template"],
        "generator_code": teacher + generator,
        "verifier_code": verifier,
    }


# ----------------------------------------------------------------------------
# Validation gates
# ----------------------------------------------------------------------------

def _probe_assignments(seed: dict) -> list[tuple[str, dict]]:
    base = prompts.seed_assignment(seed)
    out = []
    for s in seed["slots"]:
        v = s["value"]
        cands = [v * 2, v * 3, v + 1] if s["kind"] == "int" else [v * 2, v * 1.5, v + 0.5]
        for c in cands:
            a = dict(base)
            a[s["name"]] = c
            out.append((s["name"], a))
    return out


def validate(spec_text: str, seed: dict, attempt: int, xcheck: bool, solve_code: str | None) -> dict:
    """Run the gates on one Teacher output.  Returns {'ok', 'feedback', 'spec', 'stage', ...}."""
    names = [s["name"] for s in seed["slots"]]
    spec, err = parse_spec(spec_text)
    if spec is None:
        return {"ok": False, "stage": "schema", "feedback": err}
    tp = sandbox.template_problem(spec["template"], names)
    if tp:
        return {"ok": False, "stage": "schema", "feedback": tp, "spec": spec}
    for key in ("generator", "verifier"):
        sp = sandbox.static_problem(spec[key])
        if sp:
            return {"ok": False, "stage": "compile", "feedback": f"{key}: {sp}", "spec": spec}
    packaged = package(spec, seed)
    for key in ("generator_code", "verifier_code"):
        sp = sandbox.static_problem(packaged[key])
        if sp:
            return {"ok": False, "stage": "compile", "feedback": f"{key}: {sp}", "spec": spec}
    generator_id = f"{seed['seed_id']}_prompt{attempt}"
    keys = [sandbox.hash_seed(seed["seed_id"], generator_id, i) for i in range(1, N_VALIDATION + 1)]
    base = prompts.seed_assignment(seed)
    raw_code = rename(spec["generator"]) + "\n\n" + rename(spec["verifier"]) + "\n" + \
        "\ndef generator(rng):\n    return teacher_generator(rng)\n\ndef verifier(assign):\n    return teacher_verifier(assign)\n"
    probes = _probe_assignments(seed) if xcheck else []
    run = sandbox.run(raw_code, base, keys, probes=[p for _, p in probes], solve_code=solve_code if xcheck else None)
    if not run.get("ok"):
        return {"ok": False, "stage": "compile", "feedback": run.get("error", "spec failed to execute"), "spec": spec}
    samples = run.get("samples", [])
    gen_errors = [s["gen_error"] for s in samples if s.get("gen_error")]
    ver_errors = [s["verdict"]["error"] for s in samples if s.get("verdict", {}).get("error")]
    if len(gen_errors) + len(ver_errors) > N_VALIDATION // 2:
        msg = (gen_errors + ver_errors)[0]
        return {"ok": False, "stage": "runtime", "feedback": f"Runtime errors on sampled assignments, e.g. {msg}", "spec": spec}
    accepted = []
    bad_keys = 0
    for s in samples:
        a, v = s.get("assign"), s.get("verdict") or {}
        if a is None:
            continue
        if sorted(a) != sorted(names):
            bad_keys += 1
            continue
        lab = v.get("label")
        if v.get("valid") and isinstance(lab, (int, float)) and lab >= 0 and abs(lab - round(lab)) <= 1e-6 \
                and all(a[k] > 0 for k in names) and all(a[s2["name"]] == int(a[s2["name"]]) for s2 in seed["slots"] if s2["kind"] == "int"):
            accepted.append(s)
    if bad_keys > N_VALIDATION // 2:
        return {"ok": False, "stage": "runtime", "feedback": f"generator must return a dict with exactly the keys {names}.", "spec": spec}
    fresh = {tuple(s["assign"][k] for k in names) for s in accepted} - {tuple(base[k] for k in names)}
    if len(accepted) < MIN_YIELD * N_VALIDATION or len(fresh) < 2:
        return {"ok": False, "stage": "yield",
                "feedback": f"Low yield: only {len(accepted)}/{N_VALIDATION} generator samples were valid positive assignments "
                            f"accepted by the verifier with a non-negative integer answer ({len(fresh)} distinct new ones). "
                            "Make the generator sample values that keep divisions exact and quantities non-negative.",
                "spec": spec}
    seed_v = run.get("seed") or {}
    if not (seed_v.get("valid") and isinstance(seed_v.get("label"), (int, float))
            and abs(seed_v["label"] - seed["answer"]) <= 1e-6 * max(1, abs(seed["answer"]))):
        got = (seed_v.get("valid"), seed_v.get("label")) if not seed_v.get("error") else seed_v.get("error")
        return {"ok": False, "stage": "seed_consistency",
                "feedback": f"Seed-consistency check failed: verifier({base}) returned {got}, but the seed answer is "
                            f"{seed['answer']}. The verifier must reproduce the seed answer.",
                "spec": spec}
    result = {"ok": True, "stage": "accepted", "spec": spec, "packaged": package(spec, seed),
              "yield": len(accepted) / N_VALIDATION}
    if not xcheck:
        return result
    # Randomized cross-check gate (better variant).
    probe_v = run.get("probes", [])
    for name in names:
        labs = [pv.get("label") for (pn, _), pv in zip(probes, probe_v) if pn == name and pv.get("valid")]
        if labs and all(isinstance(lab, (int, float)) and abs(lab - seed["answer"]) <= 1e-9 for lab in labs):
            return {"ok": False, "stage": "xcheck_sensitivity",
                    "feedback": f"Fuzz test failed: changing {name} never changes the verifier's answer. The answer must be "
                                f"computed from assign['{name}'] (do not hard-code seed numbers).", "spec": spec,
                    "fallback": result}
    if solve_code is None or run.get("solve_error"):
        return {"ok": False, "stage": "xcheck_unavailable", "feedback": None, "spec": spec, "fallback": result}
    compared, mismatch = 0, None
    for s in accepted:
        sv = s.get("solve")
        if sv is None:
            continue
        compared += 1
        if abs(sv - s["verdict"]["label"]) > 1e-6 * max(1.0, abs(sv)):
            mismatch = (s["assign"], s["verdict"]["label"], sv)
            break
    if mismatch or compared < 3:
        fb = None
        if mismatch:
            fb = (f"Cross-check failed: for assignment {mismatch[0]} the verifier returns {mismatch[1]}, but an independent "
                  f"solution of the question gives {mismatch[2]}. Re-derive the calculation from the question text.")
        return {"ok": False, "stage": "xcheck_disagree" if mismatch else "xcheck_unavailable", "feedback": fb,
                "spec": spec, "fallback": result}
    result["xchecked"] = compared
    return result


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------

def load_seeds(paths: list[str]) -> list[dict]:
    seeds = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            seeds += [json.loads(line) for line in f if line.strip()]
    return seeds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", default=["data/gsm8k_vera/train_seeds.jsonl", "data/gsm8k_vera/test_seeds.jsonl"])
    ap.add_argument("--teacher", default="data/downloads/Qwen2.5-7B-Instruct")
    ap.add_argument("--outputs", default="outputs")
    ap.add_argument("--max_attempts", type=int, default=20)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--batch_size", type=int, default=48)
    ap.add_argument("--limit", type=int, default=0, help="debug: only the first N seeds")
    ap.add_argument("--workers", type=int, default=max(1, min(32, os.cpu_count() or 1)))
    args = ap.parse_args()

    from .llm import ChatLM

    seeds = load_seeds(args.seeds)
    if args.limit:
        seeds = seeds[: args.limit]
    out_root = Path(args.outputs)
    cache_dir = out_root / "_teacher_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "generations.jsonl"
    lm = ChatLM(args.teacher, batch_size=args.batch_size)
    if cache_file.is_file():
        for line in cache_file.open(encoding="utf-8"):
            row = json.loads(line)
            lm.cache[tuple(row["key"])] = row["text"]
        print(f"[resume] loaded {len(lm.cache)} cached generations", flush=True)

    def flush_cache(already: set) -> None:
        with cache_file.open("a", encoding="utf-8") as f:
            for k, v in lm.cache.items():
                if k not in already:
                    f.write(json.dumps({"key": list(k), "text": v}, ensure_ascii=False) + "\n")
                    already.add(k)

    flushed = set(lm.cache)
    # name -> (cross-check gate?, retry sampling-seed offset)
    variants = {"vera_e": (False, 0), "vera_e_xcheck": (True, 0), "vera_e_seed1": (False, 1)}
    state = {v: {s["seed_id"]: {"attempts": [], "accepted": None, "feedback": None, "previous": None, "fallback": None}
                 for s in seeds} for v in variants}
    by_id = {s["seed_id"]: s for s in seeds}
    t0 = time.time()
    for attempt in range(1, args.max_attempts + 1):
        pending = [(v, sid) for v in variants for sid, st in state[v].items()
                   if st["accepted"] is None and len(st["attempts"]) < attempt]
        if not pending:
            break
        temp = 0.0 if attempt == 1 else args.temperature
        texts_by_key: dict[tuple, str] = {}
        for offset in sorted({variants[v][1] for v, _ in pending}):
            group = [(v, sid) for v, sid in pending if variants[v][1] == offset]
            convs = [prompts.teacher_messages(by_id[sid], state[v][sid]["feedback"], state[v][sid]["previous"])
                     for v, sid in group]
            for key, txt in zip(group, lm.generate(convs, temperature=temp, seed=attempt + 7919 * offset)):
                texts_by_key[key] = txt
        texts = [texts_by_key[key] for key in pending]
        solves: dict[tuple, str | None] = {}
        x_pending = [(v, sid) for v, sid in pending if variants[v][0]]
        if x_pending:
            s_convs = [prompts.solve_messages(by_id[sid]) for _, sid in x_pending]
            s_texts = lm.generate(s_convs, temperature=temp, seed=attempt + 1000, max_new_tokens=400)
            for key, txt in zip(x_pending, s_texts):
                solves[key] = parse_solve(txt)
        flush_cache(flushed)

        def check(i):
            v, sid = pending[i]
            return validate(texts[i], by_id[sid], attempt, variants[v][0], solves.get((v, sid)))

        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(check, range(len(pending))))
        stages = Counter()
        for (v, sid), text, res in zip(pending, texts, results):
            st = state[v][sid]
            st["attempts"].append({"attempt": attempt, "stage": res["stage"], "feedback": res.get("feedback"),
                                   "output": text})
            stages[(v, res["stage"])] += 1
            if res["ok"]:
                st["accepted"] = {"attempt": attempt, **res["packaged"]}
            else:
                if res.get("fallback") and st["fallback"] is None:
                    st["fallback"] = {"attempt": attempt, **res["fallback"]["packaged"]}
                st["feedback"] = res.get("feedback") or "Validation failed; re-derive the specification carefully."
                st["previous"] = text
        done = {v: sum(st["accepted"] is not None for st in state[v].values()) for v in variants}
        print(f"[round {attempt}] pending={len(pending)} accepted={done} stages={dict(stages)} "
              f"elapsed={time.time() - t0:.0f}s tokens={lm.tokens_generated}", flush=True)

    # Write variant outputs.
    summary = {}
    for name, rows in (
        ("vera_e", {sid: st["accepted"] for sid, st in state["vera_e"].items()}),
        ("vera_e_1try", {sid: (st["accepted"] if st["accepted"] and st["accepted"]["attempt"] == 1 else None)
                         for sid, st in state["vera_e"].items()}),
        ("vera_e_xcheck", {sid: (st["accepted"] or st["fallback"]) for sid, st in state["vera_e_xcheck"].items()}),
        ("vera_e_seed1", {sid: st["accepted"] for sid, st in state["vera_e_seed1"].items()}),
    ):
        d = out_root / name
        d.mkdir(parents=True, exist_ok=True)
        with (d / "specs.jsonl").open("w", encoding="utf-8") as f:
            for sid in by_id:
                row = rows.get(sid)
                if row:
                    f.write(json.dumps({k: row[k] for k in ("seed_id", "template", "generator_code", "verifier_code")},
                                       ensure_ascii=False) + "\n")
        src = name if name in variants else "vera_e"
        attempts_hist = Counter(st["accepted"]["attempt"] for st in state[src].values()
                                if st["accepted"] and (name != "vera_e_1try" or st["accepted"]["attempt"] == 1))
        summary[name] = {
            "seeds": len(by_id),
            "specs_written": sum(1 for r in rows.values() if r),
            "accepted_at_attempt": dict(sorted(attempts_hist.items())),
            "max_attempts": 1 if name == "vera_e_1try" else args.max_attempts,
        }
        if name == "vera_e_xcheck":
            summary[name]["fallback_specs"] = sum(1 for st in state[src].values() if not st["accepted"] and st["fallback"])
        with (d / "method_summary.json").open("w", encoding="utf-8") as f:
            json.dump({"variant": name, "teacher": os.path.basename(args.teacher.rstrip("/")), **summary[name]}, f, indent=2)
    for v in variants:
        with (out_root / v / "synthesis_log.jsonl").open("w", encoding="utf-8") as f:
            for sid, st in state[v].items():
                f.write(json.dumps({"seed_id": sid, "accepted_attempt": st["accepted"]["attempt"] if st["accepted"] else None,
                                    "attempts": [{k: a[k] for k in ("attempt", "stage", "feedback")} for a in st["attempts"]]},
                                   ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
