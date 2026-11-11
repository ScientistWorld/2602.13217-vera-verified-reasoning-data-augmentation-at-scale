"""Shared helpers for the baseline spec writers (templates and samplers)."""
from __future__ import annotations

import json
from pathlib import Path


def load_seeds(paths: list[str]) -> list[dict]:
    seeds = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            seeds += [json.loads(line) for line in f if line.strip()]
    return seeds


def template_from_question(seed: dict) -> str:
    q = seed["question"]
    out, last = [], 0
    for s in seed["slots"]:
        out.append(q[last:s["start"]].replace("{", "{{").replace("}", "}}"))
        out.append("{" + s["name"] + "}")
        last = s["end"]
    out.append(q[last:].replace("{", "{{").replace("}", "}}"))
    return "".join(out)


def perturbation_lines(seed: dict) -> list[str]:
    """Code lines sampling each slot uniformly in [v/2, 2v] at the seed's precision."""
    lines = []
    for s in seed["slots"]:
        if s["kind"] == "int":
            v = int(s["value"])
            lo = max(1, v // 2)
            hi = max(lo + 2, 2 * v)
            lines.append(f"a[{s['name']!r}] = rng.randint({lo}, {hi})")
        else:
            decimals = len(s["text"].split(".")[1]) if "." in s["text"] else 1
            scale = 10 ** decimals
            iv = int(round(float(s["value"]) * scale))
            lo = max(1, iv // 2)
            hi = max(lo + 2, 2 * iv)
            lines.append(f"a[{s['name']!r}] = rng.randint({lo}, {hi}) / {scale}")
    return lines


def write_specs(rows: list[dict], out_dir: str) -> None:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "specs.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
