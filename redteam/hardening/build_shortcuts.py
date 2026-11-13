"""Build the shortcut submissions used by the hardening check.

Every shortcut is derived from a reference submission (specs.jsonl) and the
visible seed files only; none of them reads eval/ or any hidden answer.

  sc_counter_generator  reference specs whose generator ignores its RNG key
                        and walks a fixed per-seed list by call count
  sc_hold_slots         reference specs whose generator only ever changes the
                        first slot (all other numbers stay at the seed value)
  sc_garbage_template   reference specs with a template that is not a question
  sc_nonfinite          NaN labels on every fresh variant
  sc_seed_echo          only the seed assignment, labelled with the seed answer
  sc_speculative_fill   reference specs plus brute-force expression specs for
                        every seed the reference did not certify at the gates
  sc_abstain            only 25 specifications, each confirmed by an independent
                        cross-check (needs --xcheck): near-perfect precision,
                        almost no coverage
  _sc_hidden_failed     a failed method whose directory name starts with "_"
  .sc_dot_empty         a hidden directory with an empty specs.jsonl

Usage:
  python redteam/hardening/build_shortcuts.py --reference outputs/vera_e/specs.jsonl \
      --expression outputs/expression_search/specs.jsonl --out tmp/hardening/shortcuts
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SEEDS = ["data/gsm8k_vera/train_seeds.jsonl", "data/gsm8k_vera/test_seeds.jsonl"]


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write(out: Path, name: str, rows: list[dict] | None) -> None:
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    if rows is not None:
        with (d / "specs.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def rename_sampler(code: str) -> str:
    """Rename the submission's top-level generator so a wrapper can call it."""
    new, n = re.subn(r"(?m)^def generator\(", "def ref_generator(", code)
    if n != 1:
        raise ValueError("expected exactly one top-level generator")
    return new


COUNTER = """
CALLS = [0]

def generator(rng):
    CALLS[0] += 1
    return ref_generator(random.Random(CALLS[0] * 7919))
"""

HOLD = """
SEED = __SEED__
VARY = __VARY__

def generator(rng):
    b = dict(SEED)
    for t in range(64):
        a = ref_generator(rng)
        if not isinstance(a, dict) or VARY not in a:
            continue
        b = dict(SEED)
        b[VARY] = a[VARY]
        if b != SEED and verifier(b)[0]:
            return b
    return b
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--expression", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--xcheck", default="", help="specs.jsonl of the cross-checked variant (for sc_abstain)")
    args = ap.parse_args()
    out = Path(args.out)
    seeds = {s["seed_id"]: s for p in SEEDS for s in load_jsonl(p)}
    ref = load_jsonl(args.reference)
    expr = {r["seed_id"]: r for r in load_jsonl(args.expression)}

    counter, hold, garbage = [], [], []
    for r in ref:
        s = seeds[r["seed_id"]]
        names = [x["name"] for x in s["slots"]]
        base = {x["name"]: x["value"] for x in s["slots"]}
        try:
            gen = rename_sampler(r["generator_code"])
        except ValueError:
            continue  # cannot wrap this generator: drop the seed (scores zero)
        counter.append({**r, "generator_code": gen + COUNTER})
        hold.append({**r, "generator_code": gen + HOLD.replace("__SEED__", repr(base)).replace("__VARY__", repr(names[0]))})
        filler = "Use the numbers above. "
        tpl = "Numbers: " + ", ".join("{" + n + "}" for n in names) + ". "
        while len(tpl) < len(s["question"]):
            tpl += filler
        garbage.append({**r, "template": tpl})
    write(out, "sc_counter_generator", counter)
    write(out, "sc_hold_slots", hold)
    write(out, "sc_garbage_template", garbage)

    nonfinite, echo = [], []
    for sid, s in seeds.items():
        names = [x["name"] for x in s["slots"]]
        base = {x["name"]: x["value"] for x in s["slots"]}
        tpl = s["question"]
        parts, last = [], 0
        for x in s["slots"]:
            parts.append(tpl[last:x["start"]].replace("{", "{{").replace("}", "}}"))
            parts.append("{" + x["name"] + "}")
            last = x["end"]
        parts.append(tpl[last:].replace("{", "{{").replace("}", "}}"))
        template = "".join(parts)
        pert = "def generator(rng):\n    a = " + repr(base) + "\n    for k in a:\n        a[k] = a[k] + rng.randint(1, 3)\n    return a\n"
        nonfinite.append({"seed_id": sid, "template": template, "generator_code": pert,
                          "verifier_code": f"def verifier(assign):\n    if assign == {base!r}:\n        return True, {s['answer']}\n    return True, float('nan')\n"})
        echo.append({"seed_id": sid, "template": template,
                     "generator_code": f"def generator(rng):\n    return {base!r}\n",
                     "verifier_code": f"def verifier(assign):\n    if assign == {base!r}:\n        return True, {s['answer']}\n    return False, None\n"})
    write(out, "sc_nonfinite", nonfinite)
    write(out, "sc_seed_echo", echo)

    covered = {r["seed_id"] for r in ref}
    write(out, "sc_speculative_fill", ref + [r for sid, r in expr.items() if sid not in covered])
    if args.xcheck and Path(args.xcheck).is_file():
        checked = [r for r in load_jsonl(args.xcheck) if "independent_solve" in r["generator_code"]]
        write(out, "sc_abstain", checked[:25])
    write(out, "_sc_hidden_failed", None)
    write(out, ".sc_dot_empty", [])
    print(f"shortcuts written to {out}")


if __name__ == "__main__":
    main()
