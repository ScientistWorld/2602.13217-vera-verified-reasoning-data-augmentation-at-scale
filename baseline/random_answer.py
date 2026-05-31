from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="outputs/vera_repro/variants.jsonl")
    parser.add_argument("--out", default="outputs/baseline/random_predictions.jsonl")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.source, "r", encoding="utf-8") as src, out.open("w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            pred = rng.randint(0, 3000)
            dst.write(json.dumps({"variant_id": row["variant_id"], "prediction": pred}, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

