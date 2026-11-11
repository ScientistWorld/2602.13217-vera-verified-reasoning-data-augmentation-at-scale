"""Brute-force spec synthesis baseline: enumerate arithmetic programs.

For each seed, search expressions over the slot values (each slot used once,
plus at most one small constant when the seed has <= 4 slots) with + - * /
until one reproduces the seed answer exactly; that expression becomes the
verifier (with non-negativity / integrality checks) and the generator samples
perturbed slot values until the verifier accepts.  This is VeRA's seed
consistency gate applied to exhaustive candidate enumeration instead of a
Teacher model: it always passes the seed anchor when it finds a match, but
coincidental matches give wrong labels on fresh assignments.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import time
from itertools import combinations

from common import load_seeds, perturbation_lines, template_from_question, write_specs

CONSTANTS = [2, 3, 4, 5, 6, 7, 8, 10, 12, 24, 60, 100, 0.5]
CAP = 2000
TIME_LIMIT = 4.0


def _key(v: float) -> float:
    return round(v, 6)


def _combine(a, b):
    (va, ta), (vb, tb) = a, b
    yield va + vb, ("+", ta, tb)
    yield va * vb, ("*", ta, tb)
    if va - vb >= 0:
        yield va - vb, ("-", ta, tb)
    if vb - va >= 0:
        yield vb - va, ("-", tb, ta)
    if vb != 0:
        yield va / vb, ("/", ta, tb)
    if va != 0:
        yield vb / va, ("/", tb, ta)


def search(leaves: list[tuple[float, object]], target: float, deadline: float):
    n = len(leaves)
    full = (1 << n) - 1
    table: dict[int, dict[float, tuple]] = {}
    for i, (v, t) in enumerate(leaves):
        table[1 << i] = {_key(v): (v, t)}
    masks = sorted(range(1, full), key=lambda m: bin(m).count("1"))
    for m in masks:
        if bin(m).count("1") < 2 or m in table:
            continue
        if time.time() > deadline:
            return None
        vals: dict[float, tuple] = {}
        sub = (m - 1) & m
        while sub:
            other = m ^ sub
            if sub < other:
                for a in table[sub].values():
                    for b in table[other].values():
                        for v, t in _combine(a, b):
                            if len(vals) >= CAP:
                                break
                            vals.setdefault(_key(v), (v, t))
            sub = (sub - 1) & m
        table[m] = vals
    # Meet in the middle at the full set.
    sub = (full - 1) & full
    tk = target
    while sub:
        other = full ^ sub
        if sub < other:
            right = table[other]
            for va, ta in table[sub].values():
                needs = [(tk - va, "+"), (va - tk, "-l"), (va + tk, "-r")]
                if va != 0:
                    needs += [(tk / va, "*")]
                if tk != 0:
                    needs += [(va / tk, "/l")]
                needs += [(va * tk, "/r")]
                for need, op in needs:
                    hit = right.get(_key(need))
                    if hit is None:
                        continue
                    vb, tb = hit
                    if op == "+":
                        return ("+", ta, tb)
                    if op == "*":
                        return ("*", ta, tb)
                    if op == "-l":
                        return ("-", ta, tb)
                    if op == "-r":
                        return ("-", tb, ta)
                    if op == "/l" and vb != 0:
                        return ("/", ta, tb)
                    if op == "/r" and va != 0:
                        return ("/", tb, ta)
        sub = (sub - 1) & full
    return None


def find_expression(seed: dict):
    slots = [(float(s["value"]), ("leaf", s["name"])) for s in seed["slots"]]
    target = float(seed["answer"])
    deadline = time.time() + TIME_LIMIT
    found = search(slots, target, deadline)
    if found or len(slots) > 4:
        return found
    for c in CONSTANTS:
        found = search(slots + [(float(c), ("const", c))], target, deadline)
        if found or time.time() > deadline:
            return found
    return None


def emit(tree, lines: list[str], counter: list[int]) -> str:
    if tree[0] == "leaf":
        return tree[1]
    if tree[0] == "const":
        return repr(float(tree[1]))
    op, left, right = tree
    a = emit(left, lines, counter)
    b = emit(right, lines, counter)
    name = f"t{counter[0]}"
    counter[0] += 1
    if op == "/":
        lines.append(f"if {b} == 0:\n        return False, None")
    lines.append(f"{name} = {a} {op} {b}")
    lines.append(f"if {name} < 0:\n        return False, None")
    return name


def build(seed: dict) -> dict | None:
    tree = find_expression(seed)
    if tree is None:
        return None
    lines: list[str] = []
    for s in seed["slots"]:
        lines.append(f"{s['name']} = assign[{s['name']!r}]")
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
    ap.add_argument("--seeds", nargs="+", default=["data/gsm8k_vera/train_seeds.jsonl", "data/gsm8k_vera/test_seeds.jsonl"])
    ap.add_argument("--out", default="outputs/expression_search")
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()
    seeds = load_seeds(args.seeds)
    with mp.Pool(args.workers or None) as pool:
        rows = pool.map(build, seeds, chunksize=4)
    found = [r for r in rows if r]
    print(f"expression_search: matched {len(found)}/{len(seeds)} seeds")
    write_specs(found, args.out)


if __name__ == "__main__":
    main()
