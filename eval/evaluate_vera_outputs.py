from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def expected_geometry_answer(row: dict) -> tuple[bool, float | None]:
    assignment = row["assignment"]
    R = float(assignment["R"])
    r = float(assignment["r"])
    if R <= 0 or r <= 0 or R <= 2 * r:
        return False, None
    if row["mode"] == "VeRA-E":
        oi2 = R * (R - 2 * r)
        ai2 = R * R - oi2
        return True, ai2 + 4 * R * r
    if row["mode"] == "VeRA-H":
        theta = float(assignment["theta"])
        if not (0 < theta < 180):
            return False, None
        d = math.sqrt(R * (R - 2 * r))
        th = math.radians(theta)
        disc = R * R - (d * math.sin(th)) ** 2
        if disc < -1e-9:
            return False, None
        ai = d * math.cos(th) + math.sqrt(max(0.0, disc))
        return True, ai * ai + 4 * R * r
    return False, None


def answer_valid(row: dict) -> bool:
    valid, expected = expected_geometry_answer(row)
    return valid and expected is not None and approx_equal(float(row["numeric_answer"]), expected)


def replay_match(row: dict) -> bool:
    return (
        json.dumps(row["first_assignment"], sort_keys=True) == json.dumps(row["second_assignment"], sort_keys=True)
        and approx_equal(float(row["first_answer"]), float(row["second_answer"]), tol=1e-12)
        and bool(row.get("match", False))
    )


def noise_judge_pass(row: dict) -> bool:
    if not answer_valid(row):
        return False
    answer = float(row["numeric_answer"])
    candidates = [answer, answer + 1.0, max(0.0, answer - 1.0), answer * 1.1 + 0.5]
    expected = [True, False, False, False]
    observed = [approx_equal(answer, candidate) for candidate in candidates]
    return observed == expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="outputs/vera_repro")
    parser.add_argument("--scores", default="scoring/scores.json")
    args = parser.parse_args()

    artifact_dir = Path(args.artifacts)
    variants = load_jsonl(artifact_dir / "variants.jsonl")
    replay_rows = load_jsonl(artifact_dir / "replay_checks.jsonl")
    h_pro_rows = load_jsonl(artifact_dir / "vera_h_pro.jsonl")
    summary = load_json(artifact_dir / "method_summary.json")

    e_rows = [row for row in variants if row["mode"] == "VeRA-E"]
    h_rows = [row for row in variants if row["mode"] == "VeRA-H"]
    valid_flags = [answer_valid(row) for row in variants]
    replay_flags = [replay_match(row) for row in replay_rows]
    h_valid_flags = [answer_valid(row) for row in h_rows]

    e_seed_consistency = mean(float(answer_valid(row)) for row in e_rows) if e_rows else 0.0
    all_valid = mean(float(flag) for flag in valid_flags) if valid_flags else 0.0
    all_replay = mean(float(flag) for flag in replay_flags) if replay_flags else 0.0
    h_noise_judge = mean(float(noise_judge_pass(row)) for row in h_rows) if h_rows else 0.0

    h_reference = 2755.94103802
    paper_example_rows = [
        row
        for row in h_rows
        if row["assignment"].get("R") == 38 and row["assignment"].get("r") == 10 and row["assignment"].get("theta") == 75
    ]
    h_observed = float(paper_example_rows[0]["numeric_answer"]) if paper_example_rows else float("nan")
    h_answer_error = abs(h_observed - h_reference) if paper_example_rows else 1e9
    h_max = max((float(row["numeric_answer"]) for row in h_rows if answer_valid(row)), default=float("-inf"))
    h_pro_answer = float(h_pro_rows[0]["numeric_answer"]) if h_pro_rows else float("-inf")
    h_pro_selected_max = 1.0 if h_pro_rows and approx_equal(h_pro_answer, h_max) and answer_valid(h_pro_rows[0]) else 0.0
    summary_h_pro = summary.get("h_pro_selected") or {}
    if summary_h_pro and h_pro_rows and summary_h_pro.get("variant_id") != h_pro_rows[0].get("variant_id"):
        raise ValueError("method_summary.json and vera_h_pro.jsonl disagree on selected H-Pro variant")

    scores = {
        "experiments": {
            "aime_geometry_vera_e_generation": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(answer_valid(row)) for row in e_rows),
                        "seed_consistency_rate": e_seed_consistency,
                        "valid_rate": all_valid,
                        "deterministic_replay_rate": all_replay,
                    }
                }
            },
            "aime_geometry_vera_h_hardening": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(flag) for flag in h_valid_flags),
                        "noise_judge_pass_rate": h_noise_judge,
                        "h_pro_selected_max": h_pro_selected_max,
                        "paper_example_answer_abs_error": h_answer_error,
                    }
                }
            },
        }
    }
    score_path = Path(args.scores)
    score_path.parent.mkdir(parents=True, exist_ok=True)
    with score_path.open("w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, sort_keys=True)
    print(json.dumps(scores, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
