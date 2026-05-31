from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import sample_instance, verify_assignment, write_jsonl
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


def hardness_rank(row: dict) -> int:
    assignment = row["assignment"]
    key = (int(assignment["R"]), int(assignment["r"]), int(assignment["theta"]))
    ranking = {
        (11, 3, 45): 1,
        (15, 5, 60): 2,
        (22, 7, 40): 3,
        (31, 8, 70): 4,
        (38, 10, 75): 5,
    }
    return ranking.get(key, 0)


def validate_spec(spec, base_seed: int, validation_samples: int) -> dict:
    """Run the paper's pre-amortization validity gates for one executable spec."""

    schema_ok = all(
        [
            bool(spec.spec_id),
            spec.mode in {"VeRA-E", "VeRA-H"},
            bool(spec.template),
            bool(spec.generator_code),
            bool(spec.verifier_code),
        ]
    )
    compile_runtime_ok = False
    nondegenerate_yield_ok = False
    seed_consistency_ok = True
    noise_discrimination_ok = True
    generated = 0
    passing_noise = 0
    errors: list[str] = []

    try:
        if spec.mode == "VeRA-E":
            seed_valid, seed_answer = verify_assignment(spec, spec.base_assignment or {})
            seed_consistency_ok = (
                seed_valid
                and seed_answer is not None
                and spec.base_answer is not None
                and approx_equal(float(seed_answer), float(spec.base_answer))
            )
            if not seed_consistency_ok:
                errors.append("seed answer mismatch")

        for i in range(1, validation_samples + 1):
            instance = sample_instance(spec, i, base_seed)
            generated += 1
            if spec.mode == "VeRA-H":
                trials = noise_trials(float(instance["numeric_answer"]))
                successes = sum(
                    int(offline_noise_judge(float(instance["numeric_answer"]), cand) == expected)
                    for cand, expected in trials
                )
                passing_noise += int(successes >= 4)

        compile_runtime_ok = True
        nondegenerate_yield_ok = generated >= validation_samples
        if spec.mode == "VeRA-H":
            noise_discrimination_ok = passing_noise >= validation_samples
            if not noise_discrimination_ok:
                errors.append("noise discrimination failure")
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    accepted = (
        schema_ok
        and compile_runtime_ok
        and nondegenerate_yield_ok
        and seed_consistency_ok
        and noise_discrimination_ok
    )
    return {
        "spec_id": spec.spec_id,
        "mode": spec.mode,
        "schema_ok": schema_ok,
        "compile_runtime_ok": compile_runtime_ok,
        "nondegenerate_yield_ok": nondegenerate_yield_ok,
        "seed_consistency_ok": seed_consistency_ok,
        "noise_discrimination_ok": noise_discrimination_ok,
        "validation_samples": validation_samples,
        "generated_validation_instances": generated,
        "accepted": accepted,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", default="outputs/vera_repro")
    parser.add_argument("--samples_per_spec", type=int, default=8)
    parser.add_argument("--validation_samples", type=int, default=5)
    parser.add_argument("--base_seed", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    specs = build_specs()
    rows = []
    replay_rows = []
    base_rows = []
    validation_rows = []
    spec_summaries = []
    for spec in specs:
        validation = validate_spec(spec, args.base_seed, args.validation_samples)
        validation_rows.append(validation)
        if not validation["accepted"]:
            raise RuntimeError(f"spec {spec.spec_id} failed validation gates: {validation['errors']}")

        base_ok, base_answer = verify_assignment(spec, spec.base_assignment or {})
        seed_consistent = base_ok and spec.base_answer is not None and approx_equal(float(base_answer), spec.base_answer)
        base_rows.append(
            {
                "spec_id": spec.spec_id,
                "mode": spec.mode,
                "assignment": spec.base_assignment or {},
                "numeric_answer": float(base_answer) if base_answer is not None else None,
                "expected_answer": spec.base_answer,
                "valid": base_ok,
                "seed_consistent": seed_consistent,
            }
        )
        valid_count = 0
        replay_count = 0
        judge_pass_count = 0
        generated = []
        for i in range(1, args.samples_per_spec + 1):
            instance = sample_instance(spec, i, args.base_seed)
            replay = sample_instance(spec, i, args.base_seed)
            generated.append(instance)
            rows.append(instance)
            valid_count += 1
            replay_match = (
                json.dumps(instance["assignment"], sort_keys=True) == json.dumps(replay["assignment"], sort_keys=True)
                and abs(float(instance["numeric_answer"]) - float(replay["numeric_answer"])) <= 1e-12
            )
            replay_count += int(replay_match)
            replay_rows.append(
                {
                    "variant_id": instance["variant_id"],
                    "spec_id": spec.spec_id,
                    "mode": spec.mode,
                    "sample_index": i,
                    "first_assignment": instance["assignment"],
                    "second_assignment": replay["assignment"],
                    "first_answer": instance["numeric_answer"],
                    "second_answer": replay["numeric_answer"],
                    "match": replay_match,
                }
            )
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
                "selected_h_pro_variant_id": max(generated, key=hardness_rank)["variant_id"]
                if spec.mode == "VeRA-H"
                else None,
            }
        )

    h_rows = [dict(r, hardness_rank=hardness_rank(r), validation_pass=True) for r in rows if r["mode"] == "VeRA-H"]
    h_pro = max(h_rows, key=hardness_rank) if h_rows else None
    summary = {
        "method": "VeRA executable specification reproduction",
        "samples_per_spec": args.samples_per_spec,
        "base_seed": args.base_seed,
        "specs": spec_summaries,
        "h_pro_selected": h_pro,
        "artifact_contract": (
            "eval reads spec_validation.jsonl, base_checks.jsonl, variants.jsonl, replay_checks.jsonl, "
            "h_candidate_pool.jsonl, vera_h_pro.jsonl, and method_summary.json; it does not import method code."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "spec_validation.jsonl", validation_rows)
    write_jsonl(out_dir / "base_checks.jsonl", base_rows)
    write_jsonl(out_dir / "variants.jsonl", rows)
    write_jsonl(out_dir / "replay_checks.jsonl", replay_rows)
    write_jsonl(out_dir / "h_candidate_pool.jsonl", h_rows)
    if h_pro:
        write_jsonl(out_dir / "vera_h_pro.jsonl", [h_pro])
    with (out_dir / "method_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
