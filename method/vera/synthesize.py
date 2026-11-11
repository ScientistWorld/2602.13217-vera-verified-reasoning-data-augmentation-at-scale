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
  vera_e_xcheck  the reference's accepted specs plus an instance-level
                 cross-check (Sec. 5.2 "randomized fuzzing"; Algorithm 1 filters
                 each VeRA-H variant by an independent check): every certified
                 label must also agree with an independently derived solve()
                 program (attached when that program agrees with the verifier on
                 at least one validation sample); seeds the reference never
                 certifies fall back to a solve()-based spec that passes the
                 same gates.
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
MIN_YIELD = 0.5
MIN_AGREE = 0.0  # attach the cross-check whenever solve() agrees with the verifier at least once


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


VERIFIER_TEMPLATE = """
def verifier(assign):
    names = __NAMES__
    if not isinstance(assign, dict) or sorted(assign) != sorted(names):
        return False, None
    for k in names:
        v = assign[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v <= 0:
            return False, None
        if k in __INTS__ and v != int(v):
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
__CHECK__    return True, int(round(y))
"""

CHECK_TEMPLATE = """    try:
        s = independent_solve(*[assign[k] for k in __NAMES__])
    except Exception:
        return False, None
    if isinstance(s, bool) or not isinstance(s, (int, float)) or s != s or abs(s - y) > 1e-6 * max(1.0, abs(s)):
        return False, None
"""

SAMPLER = """
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
"""


def package(spec: dict, seed: dict, solve_code: str | None = None) -> dict:
    """Package an accepted spec with the paper's sampler semantics: the
    submitted generator retries the Teacher generator until the verifier
    accepts (Algorithm 1, _sample_variant).  With ``solve_code`` the verifier
    additionally requires agreement with an independently derived solve()
    program (instance-level cross-check, used by the vera_e_xcheck variant)."""
    names = [s["name"] for s in seed["slots"]]
    ints = [s["name"] for s in seed["slots"] if s["kind"] == "int"]
    teacher = rename(spec["generator"]) + "\n\n" + rename(spec["verifier"]) + "\n"
    check = ""
    if solve_code:
        teacher += "\n" + re.sub(r"(?<![\w.])solve\s*\(", "independent_solve(", solve_code) + "\n"
        check = CHECK_TEMPLATE.replace("__NAMES__", repr(names))
    verifier = (VERIFIER_TEMPLATE.replace("__NAMES__", repr(names)).replace("__INTS__", repr(ints))
                .replace("__CHECK__", check))
    return {
        "seed_id": seed["seed_id"],
        "template": spec["template"],
        "generator_code": teacher + SAMPLER,
        "verifier_code": verifier,
    }


# ----------------------------------------------------------------------------
# Validation gates (paper Sec. 3.3)
# ----------------------------------------------------------------------------

def _keys(seed: dict, attempt: int) -> list[int]:
    generator_id = f"{seed['seed_id']}_prompt{attempt}"
    return [sandbox.hash_seed(seed["seed_id"], generator_id, i) for i in range(1, N_VALIDATION + 1)]


def validate(spec_text: str, seed: dict, attempt: int) -> dict:
    """Run the paper's gates on one Teacher output: schema, compile, runtime,
    non-degenerate yield of the sampler, VeRA-E seed consistency."""
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
    keys = _keys(seed, attempt)
    base = prompts.seed_assignment(seed)
    raw_code = rename(spec["generator"]) + "\n\n" + rename(spec["verifier"]) + "\n" + \
        "\ndef generator(rng):\n    return teacher_generator(rng)\n\ndef verifier(assign):\n    return teacher_verifier(assign)\n"
    run = sandbox.run(raw_code, base, keys)
    if not run.get("ok"):
        return {"ok": False, "stage": "compile", "feedback": run.get("error", "spec failed to execute"), "spec": spec}
    samples = run.get("samples", [])
    gen_errors = [s["gen_error"] for s in samples if s.get("gen_error")]
    ver_errors = [s["verdict"]["error"] for s in samples if s.get("verdict", {}).get("error")]
    if len(gen_errors) + len(ver_errors) > N_VALIDATION // 2:
        msg = (gen_errors + ver_errors)[0]
        return {"ok": False, "stage": "runtime", "feedback": f"Runtime errors on sampled assignments, e.g. {msg}", "spec": spec}
    bad_keys = sum(1 for s in samples if s.get("assign") is not None and sorted(s["assign"]) != sorted(names))
    if bad_keys > N_VALIDATION // 2:
        return {"ok": False, "stage": "runtime", "feedback": f"generator must return a dict with exactly the keys {names}.", "spec": spec}
    # Non-degenerate yield of the sampler (generator retried until the verifier accepts).
    prun = sandbox.run(packaged["generator_code"] + "\n" + packaged["verifier_code"], base, keys)
    accepted = [s for s in prun.get("samples", []) if (s.get("verdict") or {}).get("valid")]
    fresh = {tuple(s["assign"][k] for k in names) for s in accepted} - {tuple(base[k] for k in names)}
    if not prun.get("ok") or len(accepted) < MIN_YIELD * N_VALIDATION or len(fresh) < 2:
        return {"ok": False, "stage": "yield",
                "feedback": f"Low yield: even with up to 64 retries per sample, the generator produced a positive assignment "
                            f"accepted by the verifier (with a non-negative integer answer) for only {len(accepted)}/"
                            f"{N_VALIDATION} samples ({len(fresh)} distinct new ones). Make the generator sample values that "
                            "keep divisions exact and quantities non-negative.",
                "spec": spec}
    seed_v = run.get("seed") or {}
    if not (seed_v.get("valid") and isinstance(seed_v.get("label"), (int, float))
            and abs(seed_v["label"] - seed["answer"]) <= 1e-6 * max(1, abs(seed["answer"]))):
        got = (seed_v.get("valid"), seed_v.get("label")) if not seed_v.get("error") else seed_v.get("error")
        return {"ok": False, "stage": "seed_consistency",
                "feedback": f"Seed-consistency check failed: verifier({base}) returned {got}, but the seed answer is "
                            f"{seed['answer']}. The verifier must reproduce the seed answer.",
                "spec": spec}
    return {"ok": True, "stage": "accepted", "spec": spec, "packaged": packaged, "yield": len(accepted) / N_VALIDATION}


def xcheck_package(spec: dict, seed: dict, attempt: int, solve_code: str | None) -> tuple[dict, dict]:
    """Better variant: attach an instance-level cross-check against an
    independently derived solve() program when that program is usable (it
    agrees with the verifier on at least one validation sample); otherwise
    keep the plain paper-gated spec."""
    info = {"cross_checked": False, "compared": 0, "agree": 0}
    plain = package(spec, seed)
    if not solve_code or sandbox.static_problem(solve_code):
        return plain, info
    run = sandbox.run(plain["generator_code"] + "\n" + plain["verifier_code"], prompts.seed_assignment(seed),
                      _keys(seed, attempt), solve_code=solve_code)
    for s in run.get("samples", []):
        v = s.get("verdict") or {}
        if v.get("valid") and s.get("solve") is not None:
            info["compared"] += 1
            info["agree"] += int(abs(s["solve"] - v["label"]) <= 1e-6 * max(1.0, abs(s["solve"])))
    if info["compared"] >= 3 and info["agree"] >= max(1, MIN_AGREE * info["compared"]):
        checked = package(spec, seed, solve_code)
        if not any(sandbox.static_problem(checked[k]) for k in ("generator_code", "verifier_code")):
            info["cross_checked"] = True
            return checked, info
    return plain, info


def solve_spec_text(seed: dict, solve_code: str | None) -> str | None:
    """Fallback for the better variant: when the Teacher never produced an
    accepted spec, build one from the independent solve() program (verifier)
    and a generic perturbation sampler; it must pass the same gates."""
    if not solve_code:
        return None
    q = seed["question"]
    out, last = [], 0
    for sl in seed["slots"]:
        out.append(q[last:sl["start"]].replace("{", "{{").replace("}", "}}"))
        out.append("{" + sl["name"] + "}")
        last = sl["end"]
    out.append(q[last:].replace("{", "{{").replace("}", "}}"))
    lines = []
    for sl in seed["slots"]:
        if sl["kind"] == "int":
            v = int(sl["value"]); lo = max(1, v // 2); hi = max(lo + 2, 2 * v)
            lines.append(f"    a[{sl['name']!r}] = rng.randint({lo}, {hi})")
        else:
            dec = len(sl["text"].split(".")[1]) if "." in sl["text"] else 1
            sc = 10 ** dec; iv = int(round(float(sl["value"]) * sc)); lo = max(1, iv // 2); hi = max(lo + 2, 2 * iv)
            lines.append(f"    a[{sl['name']!r}] = rng.randint({lo}, {hi}) / {sc}")
    gen = "def generator(rng):\n    a = {}\n" + "\n".join(lines) + "\n    return a\n"
    names = [sl["name"] for sl in seed["slots"]]
    ver = solve_code + "\n\ndef verifier(assign):\n    return True, solve(*[assign[k] for k in " + repr(names) + "])\n"
    return json.dumps({"template": "".join(out), "generator": gen, "verifier": ver})


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------

def write_outputs(state: dict, by_id: dict, variants: dict, out_root: Path, args) -> dict:
    """Write specs/logs for every variant (called after each round, so a preempted run keeps its progress)."""
    summary = {}
    for name, rows in (
        ("vera_e", {sid: st["accepted"] for sid, st in state["vera_e"].items()}),
        ("vera_e_1try", {sid: (st["accepted"] if st["accepted"] and st["accepted"]["attempt"] == 1 else None)
                         for sid, st in state["vera_e"].items()}),
        ("vera_e_seed1", {sid: st["accepted"] for sid, st in state["vera_e_seed1"].items()}),
        ("vera_e_xcheck", {sid: st["xcheck"] for sid, st in state["vera_e"].items()}),
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
            summary[name]["cross_checked_specs"] = sum(1 for st in state["vera_e"].values()
                                                       if st["xcheck"] and st["xcheck"]["info"].get("cross_checked"))
            summary[name]["solve_fallback_specs"] = sum(1 for st in state["vera_e"].values()
                                                        if st["xcheck"] and st["xcheck"]["info"].get("solve_fallback"))
        with (d / "method_summary.json").open("w", encoding="utf-8") as f:
            json.dump({"variant": name, "teacher": os.path.basename(args.teacher.rstrip("/")), **summary[name]}, f, indent=2)
    for v in variants:
        with (out_root / v / "synthesis_log.jsonl").open("w", encoding="utf-8") as f:
            for sid, st in state[v].items():
                f.write(json.dumps({"seed_id": sid, "accepted_attempt": st["accepted"]["attempt"] if st["accepted"] else None,
                                    "attempts": [{k: a[k] for k in ("attempt", "stage", "feedback")} for a in st["attempts"]]},
                                   ensure_ascii=False) + "\n")
    return summary


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
    ap.add_argument("--max_attempts", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--batch_size", type=int, default=48)
    ap.add_argument("--limit", type=int, default=0, help="debug: only the first N seeds")
    ap.add_argument("--replay_only", action="store_true",
                    help="rebuild outputs from outputs/_teacher_cache without a GPU (fails on a cache miss)")
    ap.add_argument("--workers", type=int, default=max(1, min(32, os.cpu_count() or 1)))
    args = ap.parse_args()


    seeds = load_seeds(args.seeds)
    if args.limit:
        seeds = seeds[: args.limit]
    out_root = Path(args.outputs)
    cache_dir = out_root / "_teacher_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "generations.jsonl"
    if args.replay_only:
        from .llm import ReplayLM

        lm = ReplayLM()
    else:
        from .llm import ChatLM

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
    # name -> retry sampling-seed offset.  vera_e_seed1 reruns the reference with
    # different retry samples (noise estimate); vera_e_1try and vera_e_xcheck are
    # derived from vera_e's own trajectory.
    variants = {"vera_e": 0, "vera_e_seed1": 1}
    state = {v: {s["seed_id"]: {"attempts": [], "accepted": None, "feedback": None, "previous": None, "xcheck": None}
                 for s in seeds} for v in variants}
    by_id = {s["seed_id"]: s for s in seeds}
    t0 = time.time()
    # Independent solve() programs for the cross-check variant (one greedy call per seed).
    solve_texts = lm.generate([prompts.solve_messages(s) for s in seeds], temperature=0.0, seed=1001, max_new_tokens=400)
    solves = {s["seed_id"]: parse_solve(t) for s, t in zip(seeds, solve_texts)}
    flush_cache(flushed)
    for attempt in range(1, args.max_attempts + 1):
        pending = [(v, sid) for v in variants for sid, st in state[v].items()
                   if st["accepted"] is None and len(st["attempts"]) < attempt]
        if not pending:
            break
        temp = 0.0 if attempt == 1 else args.temperature
        texts_by_key: dict[tuple, str] = {}
        for offset in sorted({variants[v] for v, _ in pending}):
            group = [(v, sid) for v, sid in pending if variants[v] == offset]
            convs = [prompts.teacher_messages(by_id[sid], state[v][sid]["feedback"], state[v][sid]["previous"])
                     for v, sid in group]
            for key, txt in zip(group, lm.generate(convs, temperature=temp, seed=attempt + 7919 * offset)):
                texts_by_key[key] = txt
        texts = [texts_by_key[key] for key in pending]
        flush_cache(flushed)

        def check(i):
            v, sid = pending[i]
            res = validate(texts[i], by_id[sid], attempt)
            if res["ok"] and v == "vera_e":
                pk, info = xcheck_package(res["spec"], by_id[sid], attempt, solves.get(sid))
                res["xcheck"] = {"attempt": attempt, **pk, "info": info}
            return res

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
                st["xcheck"] = res.get("xcheck")
            else:
                st["feedback"] = res.get("feedback") or "Validation failed; re-derive the specification carefully."
                st["previous"] = text
        done = {v: sum(st["accepted"] is not None for st in state[v].values()) for v in variants}
        print(f"[round {attempt}] pending={len(pending)} accepted={done} stages={dict(stages)} "
              f"elapsed={time.time() - t0:.0f}s tokens={lm.tokens_generated}", flush=True)
        write_outputs(state, by_id, variants, out_root, args)

    # Better variant fallback: seeds the reference never certified get a
    # solve()-based spec if it passes the same gates.
    def fallback(sid):
        text = solve_spec_text(by_id[sid], solves.get(sid))
        if text is None:
            return sid, None
        res = validate(text, by_id[sid], args.max_attempts + 1)
        if not res["ok"]:
            return sid, None
        return sid, {"attempt": args.max_attempts + 1, **res["packaged"],
                     "info": {"cross_checked": False, "solve_fallback": True}}

    missing = [sid for sid, st in state["vera_e"].items() if st["accepted"] is None]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for sid, row in pool.map(fallback, missing):
            if row:
                state["vera_e"][sid]["xcheck"] = row
    summary = write_outputs(state, by_id, variants, out_root, args)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
