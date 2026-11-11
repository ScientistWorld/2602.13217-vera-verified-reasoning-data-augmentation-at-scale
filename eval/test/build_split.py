"""Build the GSM8K VeRA-E seed split and the hidden reference programs.

This script lives in eval/test/ because it is the only code that can
regenerate the hidden test labels.  It is run once by the gym builder; its
outputs are committed:

  data/gsm8k_vera/train_seeds.jsonl   visible train seeds (question, answer,
                                      slot schema, worked solution)
  data/gsm8k_vera/test_seeds.jsonl    visible test seeds (question, answer,
                                      slot schema only -- no solution)
  eval/train/references.jsonl         visible train reference programs
  eval/test/references.jsonl          hidden test reference programs

A reference program is the seed's own latent computation, recovered from the
GSM8K calculator annotations (``<<48/2=24>>``): every number literal in an
annotation is mapped to a question number (slot), to an earlier intermediate
result, or to a small unit constant.  Seeds whose mapping is ambiguous are
dropped, so the remaining programs reproduce the gold answer at the seed and
keep their meaning when the slot values change.

Usage (needs the raw GSM8K files from github.com/openai/grade-school-math):
  python eval/test/build_split.py --gsm8k_dir <dir with train.jsonl,test.jsonl>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\w])")
CALC_RE = re.compile(r"<<([^=<>]+)=([^<>]+)>>")
TOK_RE = re.compile(r"\d+(?:\.\d+)?|\.\d+|[()+\-*/]")
ALLOWED_CONST = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 24.0, 30.0,
                 52.0, 60.0, 100.0, 365.0, 1000.0, 0.5, 0.25, 0.1, 0.01}
# A digit in the question whose value is also a common implicit constant is
# ambiguous when the matching cue word occurs (e.g. "2 bolts ... half").
CUES = {
    2.0: ["half", "twice", "double", "two", "pair", "both", "halves", "second"],
    3.0: ["third", "triple", "thrice", "three"],
    4.0: ["quarter", "four", "fourth"],
    5.0: ["five", "fifth", "nickel"],
    6.0: ["six", "sixth", "half dozen", "half a dozen"],
    7.0: ["week", "seven"],
    8.0: ["eight", "eighth"],
    9.0: ["nine", "ninth"],
    10.0: ["ten", "tenth", "dime", "decade", "percent", "%"],
    12.0: ["dozen", "month", "year", "foot", "feet", "inch", "twelve"],
    24.0: ["day", "hour"],
    30.0: ["month", "day"],
    52.0: ["week", "year"],
    60.0: ["hour", "minute", "second"],
    100.0: ["percent", "%", "cent", "century", "hundred"],
    365.0: ["year", "day"],
    1000.0: ["thousand", "kilo", "liter", "litre", "meter", "metre", "gram"],
    1.0: ["one", "each", "per", "every", "a "],
}
MIN_SLOTS, MAX_SLOTS = 2, 6
MIN_STEPS = 2


def question_numbers(q: str) -> list[dict]:
    out = []
    for m in NUM_RE.finditer(q):
        text = m.group(0)
        value = float(text.replace(",", ""))
        out.append({"text": text, "value": value, "start": m.start(), "end": m.end(),
                    "kind": "float" if m.group(2) else "int"})
    return out


def safe_eval(expr: str, env: dict) -> float:
    return float(eval(expr, {"__builtins__": {}}, env))  # expr built from our own tokens only


def derive(q: str, solution: str) -> tuple[dict | None, str]:
    ans_text = solution.split("####")[-1].strip().replace(",", "")
    try:
        answer = float(ans_text)
    except ValueError:
        return None, "bad_answer"
    if answer < 0 or abs(answer - round(answer)) > 1e-9:
        return None, "non_integer_answer"
    nums = question_numbers(q)
    values = [n["value"] for n in nums]
    if not (MIN_SLOTS <= len(nums) <= MAX_SLOTS):
        return None, "slot_count"
    if len(set(values)) != len(values):
        return None, "duplicate_question_numbers"
    if any(v <= 0 for v in values):
        return None, "nonpositive_slot"
    low = q.lower()
    for v in values:
        for cue in CUES.get(v, []):
            if cue in low:
                return None, "cue_ambiguity"
    calcs = CALC_RE.findall(solution)
    if not calcs:
        return None, "no_annotations"
    steps: list[str] = []
    results: list[float] = []
    used = set()
    for expr, res in calcs:
        try:
            res_v = float(res.replace(",", "").replace("$", "").strip())
        except ValueError:
            return None, "bad_result"
        clean = expr.replace(",", "").replace(" ", "").replace("$", "")
        toks = TOK_RE.findall(clean)
        if "".join(toks) != clean:
            return None, "bad_tokens"
        out = []
        for t in toks:
            if t in "()+-*/":
                out.append(t)
                continue
            v = float(t)
            qm = [i for i, x in enumerate(values) if abs(x - v) < 1e-9]
            rm = [j for j, x in enumerate(results) if abs(x - v) < 1e-9]
            if qm and rm:
                return None, "slot_vs_intermediate_ambiguity"
            if len(rm) > 1:
                return None, "intermediate_ambiguity"
            if rm and v in ALLOWED_CONST:
                return None, "intermediate_vs_constant_ambiguity"
            if qm:
                out.append(f"n{qm[0]}")
                used.add(qm[0])
            elif rm:
                out.append(f"r{rm[0]}")
            elif v in ALLOWED_CONST:
                out.append(repr(v))
            else:
                return None, "unknown_constant"
        step = "".join(out)
        env = {f"n{i}": x for i, x in enumerate(values)}
        env.update({f"r{j}": x for j, x in enumerate(results)})
        try:
            got = safe_eval(step, env)
        except Exception:
            return None, "eval_error"
        if abs(got - res_v) > 1e-6 * max(1.0, abs(res_v)):
            return None, "annotation_mismatch"
        if got < 0:
            return None, "negative_intermediate"
        results.append(got)
        steps.append(step)
    if abs(results[-1] - answer) > 1e-6 * max(1.0, abs(answer)):
        return None, "final_mismatch"
    if used != set(range(len(values))):
        return None, "unused_slot"
    if len(steps) < MIN_STEPS:
        return None, "too_few_steps"
    return {"answer": answer, "slots": nums, "steps": steps}, "ok"


def stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsm8k_dir", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--n_train", type=int, default=300)
    ap.add_argument("--n_test", type=int, default=800)
    args = ap.parse_args()
    root = Path(args.root)

    pools: dict[str, list[dict]] = {"test": [], "train": []}
    for split in ("test", "train"):
        stats: Counter = Counter()
        for idx, line in enumerate(open(Path(args.gsm8k_dir) / f"{split}.jsonl", encoding="utf-8")):
            d = json.loads(line)
            ref, why = derive(d["question"], d["answer"])
            stats[why] += 1
            if ref is None:
                continue
            ref.update({"question": d["question"], "solution": d["answer"],
                        "origin": f"gsm8k_{split}_{idx}"})
            pools[split].append(ref)
        print(split, dict(stats))

    rng = random.Random(20260211)
    gsm_test = sorted(pools["test"], key=lambda r: stable_hash(r["origin"]))
    gsm_train = sorted(pools["train"], key=lambda r: stable_hash(r["origin"]))
    rng.shuffle(gsm_train)
    test = gsm_test[: args.n_test]
    extra = args.n_test - len(test)
    test += gsm_train[:extra]
    rest = gsm_train[extra:]
    # Train seeds: match the test step-count distribution.
    want = Counter(min(len(r["steps"]), 5) for r in test)
    by_bucket: dict[int, list[dict]] = {}
    for r in rest:
        by_bucket.setdefault(min(len(r["steps"]), 5), []).append(r)
    train = []
    for bucket, count in sorted(want.items()):
        k = round(count * args.n_train / len(test))
        train += by_bucket.get(bucket, [])[:k]
    train = train[: args.n_train]

    def seed_row(r: dict, sid: str, with_solution: bool) -> dict:
        row = {
            "seed_id": sid,
            "question": r["question"],
            "answer": int(round(r["answer"])),
            "slots": [{"name": f"n{i}", "text": s["text"], "value": int(s["value"]) if s["kind"] == "int" else s["value"],
                       "kind": s["kind"], "start": s["start"], "end": s["end"]} for i, s in enumerate(r["slots"])],
        }
        if with_solution:
            row["solution"] = r["solution"]
        return row

    def ref_row(r: dict, sid: str) -> dict:
        return {
            "seed_id": sid,
            "answer": int(round(r["answer"])),
            "slot_kinds": {f"n{i}": s["kind"] for i, s in enumerate(r["slots"])},
            "seed_assignment": {f"n{i}": (int(s["value"]) if s["kind"] == "int" else s["value"]) for i, s in enumerate(r["slots"])},
            "steps": r["steps"],
            "n_steps": len(r["steps"]),
            "origin": r["origin"],
        }

    (root / "data/gsm8k_vera").mkdir(parents=True, exist_ok=True)
    for split, rows, prefix, with_solution, ref_dir in (
        ("train", train, "tr", True, "eval/train"),
        ("test", test, "te", False, "eval/test"),
    ):
        seeds = [seed_row(r, f"{prefix}{i:04d}", with_solution) for i, r in enumerate(rows)]
        refs = [ref_row(r, f"{prefix}{i:04d}") for i, r in enumerate(rows)]
        with open(root / f"data/gsm8k_vera/{split}_seeds.jsonl", "w", encoding="utf-8") as f:
            for s in seeds:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        with open(root / ref_dir / "references.jsonl", "w", encoding="utf-8") as f:
            for s in refs:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(split, len(rows), "steps", sorted(Counter(len(r["steps"]) for r in rows).items()),
              "slots", sorted(Counter(len(r["slots"]) for r in rows).items()))


if __name__ == "__main__":
    main()
