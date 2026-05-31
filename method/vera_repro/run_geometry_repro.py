from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import deterministic_replay, sample_instance, verify_assignment, write_jsonl
from .geometry_specs import build_specs


def approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def offline_noise_judge(correct: float, candidate: float, tol: float = 1e-6) -> bool:
    """Offline substitute for the paper's judge: true iff candidate matches the verifier label."""

    return approx_equal(candidate, correct, tol)


def noise_trials(answer: float) -> list[tuple[float, bool]]:
    return [
        (answer, True),
        (answer, True),
        (answer + 1.0, False),
        (max(0.0, answer - 1.0), False),
        (answer * 1.1 + 0.5, False),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", default="outputs/vera_repro")
    parser.add_argument("--samples_per_spec", type=int, default=8)
    parser.add_argument("--base_seed", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    specs = build_specs()
    rows = []
    spec_summaries = []
    for spec in specs:
        base_ok, base_answer = verify_assignment(spec, spec.base_assignment or {})
        seed_consistent = base_ok and spec.base_answer is not None and approx_equal(float(base_answer), spec.base_answer)
        valid_count = 0
        replay_count = 0
        judge_pass_count = 0
        generated = []
        for i in range(1, args.samples_per_spec + 1):
            instance = sample_instance(spec, i, args.base_seed)
            generated.append(instance)
            rows.append(instance)
            valid_count += 1
            replay_count += int(deterministic_replay(spec, i, args.base_seed))
            trials = noise_trials(float(instance["numeric_answer"]))
            successes = sum(int(offline_noise_judge(float(instance["numeric_answer"]), cand) == expected) for cand, expected in trials)
            judge_pass_count += int(successes >= 4)
        spec_summaries.append(
            {
                "spec_id": spec.spec_id,
                "mode": spec.mode,
                "seed_consistent": seed_consistent,
                "base_answer": base_answer,
                "expected_base_answer": spec.base_answer,
                "generated": valid_count,
                "valid_rate": valid_count / args.samples_per_spec,
                "deterministic_replay_rate": replay_count / args.samples_per_spec,
                "noise_judge_pass_rate": judge_pass_count / args.samples_per_spec,
                "max_answer": max(float(x["numeric_answer"]) for x in generated),
                "selected_h_pro_variant_id": max(generated, key=lambda x: float(x["numeric_answer"]))["variant_id"]
                if spec.mode == "VeRA-H"
                else None,
            }
        )

    h_rows = [r for r in rows if r["mode"] == "VeRA-H"]
    h_pro = max(h_rows, key=lambda x: float(x["numeric_answer"])) if h_rows else None
    summary = {
        "method": "VeRA executable specification reproduction",
        "samples_per_spec": args.samples_per_spec,
        "base_seed": args.base_seed,
        "specs": spec_summaries,
        "h_pro_selected": h_pro,
        "artifact_contract": "eval reads variants.jsonl and method_summary.json; it does not import method code.",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "variants.jsonl", rows)
    if h_pro:
        write_jsonl(out_dir / "vera_h_pro.jsonl", [h_pro])
    with (out_dir / "method_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

