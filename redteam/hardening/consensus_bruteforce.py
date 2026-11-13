"""Stronger brute force: expression enumeration with a consensus filter.

baseline/expression_search.py emits the first arithmetic program over the slot
values that reproduces the seed answer, and fails the precision floor because
coincidental matches mislabel fresh variants.  This variant enumerates the
matching programs as *functions* (every sub-expression is evaluated at the
seed and at N_PROBES perturbed assignments at once) and emits a spec only when
all programs that reproduce the seed answer agree at every probe, i.e. when
the seed answer pins the program down.  It abstains otherwise.

Usage:
  python redteam/hardening/consensus_bruteforce.py --out tmp/hardening/shortcuts/sc_consensus_bruteforce \
      --seeds data/gsm8k_vera/test_seeds.jsonl
"""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "baseline"))
from common import load_seeds, perturbation_lines, template_from_question, write_specs  # noqa: E402
from expression_search import CONSTANTS, emit  # noqa: E402

N_PROBES = 4
CAP = 1500
TIME_LIMIT = 3.0


def probe_columns(seed: dict) -> list[tuple]:
    rng = random.Random("probe|" + seed["seed_id"])
    rows = [[float(s["value"]) for s in seed["slots"]]]
    for _ in range(N_PROBES):
        row = []
        for s in seed["slots"]:
            if s["kind"] == "int":
                v = int(s["value"]); lo = max(1, v // 2); hi = max(lo + 2, 2 * v)
                row.append(float(rng.randint(lo, hi)))
            else:
                dec = len(s["text"].split(".")[1]) if "." in s["text"] else 1
                sc = 10 ** dec; iv = int(round(float(s["value"]) * sc)); lo = max(1, iv // 2); hi = max(lo + 2, 2 * iv)
                row.append(rng.randint(lo, hi) / sc)
        rows.append(row)
    return [tuple(col) for col in zip(*rows)]


def fkey(vec: tuple) -> tuple:
    return tuple(round(x, 6) for x in vec)


def combine(a, b):
    (va, ta), (vb, tb) = a, b
    yield tuple(x + y for x, y in zip(va, vb)), ("+", ta, tb)
    yield tuple(x * y for x, y in zip(va, vb)), ("*", ta, tb)
    yield tuple(x - y for x, y in zip(va, vb)), ("-", ta, tb)
    yield tuple(y - x for x, y in zip(va, vb)), ("-", tb, ta)
    if all(y != 0 for y in vb):
        yield tuple(x / y for x, y in zip(va, vb)), ("/", ta, tb)
    if all(x != 0 for x in va):
        yield tuple(y / x for x, y in zip(va, vb)), ("/", tb, ta)


def ok(vec: tuple) -> bool:
    return vec[0] >= -1e-9 and all(math.isfinite(x) and abs(x) < 1e12 for x in vec)


def matching_functions(leaves: list[tuple], target: float, deadline: float) -> dict | None:
    """Map function-key -> tree for every program over all leaves whose seed value is target."""
    n = len(leaves)
    full = (1 << n) - 1
    table: dict[int, dict] = {1 << i: {fkey(v): (v, t)} for i, (v, t) in enumerate(leaves)}
    for m in sorted(range(1, full), key=lambda m: bin(m).count("1")):
        if bin(m).count("1") < 2:
            continue
        vals: dict = {}
        sub = (m - 1) & m
        while sub:
            other = m ^ sub
            if sub < other:
                for a in table[sub].values():
                    for b in table[other].values():
                        for v, t in combine(a, b):
                            if len(vals) < CAP and ok(v):
                                vals.setdefault(fkey(v), (v, t))
                if time.time() > deadline:
                    return None
            sub = (sub - 1) & m
        table[m] = vals
    found: dict = {}
    sub = (full - 1) & full
    while sub:
        other = full ^ sub
        if sub < other:
            for a in table[sub].values():
                for b in table[other].values():
                    for v, t in combine(a, b):
                        if abs(v[0] - target) <= 1e-6 * max(1.0, abs(target)) and ok(v):
                            found.setdefault(fkey(v[1:]), t)
            if time.time() > deadline:
                return None
        sub = (sub - 1) & full
    return found


def find_unique(seed: dict):
    cols = probe_columns(seed)
    leaves = [(col, ("leaf", s["name"])) for col, s in zip(cols, seed["slots"])]
    target = float(seed["answer"])
    deadline = time.time() + TIME_LIMIT
    if len(leaves) == 1:
        return None
    found = matching_functions(leaves, target, deadline)
    if found is None:
        return None
    if not found and len(leaves) <= 4:
        found = {}
        for c in CONSTANTS:
            more = matching_functions(leaves + [((float(c),) * len(cols[0]), ("const", c))], target, deadline)
            if more is None:
                return None
            found.update(more)
    if len(found) != 1:
        return None  # abstain: no program, or several programs that disagree off the seed
    return next(iter(found.values()))


def build(seed: dict) -> dict | None:
    tree = find_unique(seed)
    if tree is None:
        return None
    lines: list[str] = [f"{s['name']} = assign[{s['name']!r}]" for s in seed["slots"]]
    result = emit(tree, lines, [0])
    lines.append(f"if abs({result} - round({result})) > 1e-6:\n        return False, None")
    lines.append(f"return True, int(round({result}))")
    ver = "def verifier(assign):\n" + "".join(f"    {line}\n" for line in lines)
    gen = ("def generator(rng):\n    a = {}\n    for attempt in range(200):\n"
           + "".join(f"        {line}\n" for line in perturbation_lines(seed))
           + "        if verifier(dict(a))[0]:\n            return a\n    return a\n")
    return {"seed_id": seed["seed_id"], "template": template_from_question(seed), "generator_code": gen, "verifier_code": ver}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", default=["data/gsm8k_vera/test_seeds.jsonl"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()
    seeds = load_seeds(args.seeds)
    with mp.Pool(args.workers or None) as pool:
        rows = pool.map(build, seeds, chunksize=2)
    found = [r for r in rows if r]
    print(f"consensus_bruteforce: emitted {len(found)}/{len(seeds)} seeds")
    write_specs(found, args.out)


if __name__ == "__main__":
    main()
