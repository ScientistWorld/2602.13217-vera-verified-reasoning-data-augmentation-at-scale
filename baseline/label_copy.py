"""Naive augmentation baseline: perturb the numbers, keep the seed's label.

This is the unverified "surface perturbation" family that the paper contrasts
VeRA with: the question changes but the label is copied from the seed, so the
label is wrong whenever the answer depends on the changed numbers.
"""
from __future__ import annotations

import argparse

from common import load_seeds, perturbation_lines, template_from_question, write_specs


def build(seed: dict) -> dict:
    gen = "def generator(rng):\n    a = {}\n" + "".join(f"    {line}\n" for line in perturbation_lines(seed)) + "    return a\n"
    ver = f"def verifier(assign):\n    return True, {int(seed['answer'])}\n"
    return {"seed_id": seed["seed_id"], "template": template_from_question(seed), "generator_code": gen, "verifier_code": ver}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", default=["data/gsm8k_vera/train_seeds.jsonl", "data/gsm8k_vera/test_seeds.jsonl"])
    ap.add_argument("--out", default="outputs/label_copy")
    args = ap.parse_args()
    write_specs([build(s) for s in load_seeds(args.seeds)], args.out)


if __name__ == "__main__":
    main()
