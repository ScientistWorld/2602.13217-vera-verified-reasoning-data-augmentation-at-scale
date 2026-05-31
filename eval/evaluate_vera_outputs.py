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


def load_optional_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return load_jsonl(path)


def approx_equal(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def expected_answer(row: dict) -> tuple[bool, float | None]:
    spec_id = row["spec_id"]
    assignment = row["assignment"]

    if spec_id == "aime2024_ii_10_vera_e":
        R = float(assignment["R"])
        r = float(assignment["r"])
        if R <= 0 or r <= 0 or R <= 2 * r:
            return False, None
        oi2 = R * (R - 2 * r)
        ai2 = R * R - oi2
        return True, ai2 + 4 * R * r

    if spec_id == "aime2024_ii_10_vera_h":
        R = float(assignment["R"])
        r = float(assignment["r"])
        if R <= 0 or r <= 0 or R <= 2 * r:
            return False, None
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

    if spec_id == "aime2024_ii_9_chip_grid_vera_e":
        rows = int(assignment["rows"])
        cols = int(assignment["cols"])
        cap_a = int(assignment["color_a_count"])
        cap_b = int(assignment["color_b_count"])
        if rows <= 0 or cols <= 0 or cap_a < 0 or cap_b < 0:
            return False, None
        total = 0
        for row_mask in range(1 << rows):
            a_rows = row_mask.bit_count()
            b_rows = rows - a_rows
            for col_mask in range(1 << cols):
                a_cols = col_mask.bit_count()
                b_cols = cols - a_cols
                if (a_rows > 0, b_rows > 0) != (a_cols > 0, b_cols > 0):
                    continue
                used_a = a_rows * a_cols
                used_b = b_rows * b_cols
                if used_a <= cap_a and used_b <= cap_b:
                    total += 1
        return True, float(total)

    if spec_id == "aime2024_i_11_polygon_rotation_vera_e":
        n = int(assignment["n"])
        if n < 3 or n > 20:
            return False, None
        favorable = 0
        for mask in range(1 << n):
            works = False
            for shift in range(1, n):
                shifted = ((mask << shift) | (mask >> (n - shift))) & ((1 << n) - 1)
                if mask & shifted == 0:
                    works = True
                    break
            favorable += int(works)
        denom = 1 << n
        gcd = math.gcd(favorable, denom)
        return True, float(favorable // gcd + denom // gcd)

    return False, None


def answer_valid(row: dict) -> bool:
    valid, expected = expected_answer(row)
    return valid and expected is not None and approx_equal(float(row["numeric_answer"]), expected)


def base_check_valid(row: dict) -> bool:
    valid, expected = expected_answer(row)
    expected_seed = row.get("expected_answer")
    observed = row.get("numeric_answer")
    return (
        valid
        and expected is not None
        and expected_seed is not None
        and observed is not None
        and approx_equal(float(observed), expected)
        and approx_equal(float(observed), float(expected_seed))
        and bool(row.get("valid", False))
        and bool(row.get("seed_consistent", False))
    )


def replay_match(row: dict) -> bool:
    return (
        json.dumps(row["first_assignment"], sort_keys=True) == json.dumps(row["second_assignment"], sort_keys=True)
        and approx_equal(float(row["first_answer"]), float(row["second_answer"]), tol=1e-12)
        and bool(row.get("match", False))
    )


def assignment_key(row: dict) -> str:
    return json.dumps(row.get("assignment", {}), sort_keys=True, separators=(",", ":"))


def valid_assignment_diversity_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    unique_valid = {assignment_key(row) for row in rows if answer_valid(row)}
    return len(unique_valid) / len(rows)


def valid_spec_coverage_rate(rows: list[dict], expected_specs: set[str]) -> float:
    if not expected_specs:
        return 0.0
    covered = {row["spec_id"] for row in rows if row["spec_id"] in expected_specs and answer_valid(row)}
    return len(covered) / len(expected_specs)


def valid_seed_answer_novelty_rate(rows: list[dict], seed_answers: dict[str, float]) -> float:
    if not rows:
        return 0.0
    novel_valid = 0
    for row in rows:
        seed_answer = seed_answers.get(row["spec_id"])
        if seed_answer is None:
            continue
        novel_valid += int(answer_valid(row) and not approx_equal(float(row["numeric_answer"]), seed_answer))
    return novel_valid / len(rows)


def valid_hardness_diversity_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    unique_valid = {h_hardness_rank(row) for row in rows if answer_valid(row)}
    return len(unique_valid) / len(rows)


def valid_mean_hardness_rank_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    rank_sum = sum(h_hardness_rank(row) for row in rows if answer_valid(row))
    return rank_sum / (len(rows) * 5.0)


def validation_gate_pass_rate(rows: list[dict], expected_specs: set[str]) -> float:
    if not expected_specs:
        return 0.0
    accepted = {
        row["spec_id"]
        for row in rows
        if row.get("spec_id") in expected_specs
        and bool(row.get("schema_ok"))
        and bool(row.get("compile_runtime_ok"))
        and bool(row.get("nondegenerate_yield_ok"))
        and bool(row.get("accepted"))
    }
    return len(accepted) / len(expected_specs)


def h_candidate_pool_valid_rate(rows: list[dict]) -> float:
    if not rows:
        return 0.0
    return mean(float(bool(row.get("validation_pass")) and answer_valid(row)) for row in rows)


def noise_judge_pass(row: dict) -> bool:
    if not answer_valid(row):
        return False
    answer = float(row["numeric_answer"])
    candidates = [answer, answer + 1.0, max(0.0, answer - 1.0), answer * 1.1 + 0.5]
    expected = [True, False, False, False]
    observed = [approx_equal(answer, candidate) for candidate in candidates]
    return observed == expected


def h_hardness_rank(row: dict) -> int:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="outputs/vera_repro")
    parser.add_argument("--scores", default="scoring/scores.json")
    args = parser.parse_args()

    artifact_dir = Path(args.artifacts)
    base_rows = load_jsonl(artifact_dir / "base_checks.jsonl")
    variants = load_jsonl(artifact_dir / "variants.jsonl")
    replay_rows = load_jsonl(artifact_dir / "replay_checks.jsonl")
    h_pro_rows = load_jsonl(artifact_dir / "vera_h_pro.jsonl")
    validation_rows = load_optional_jsonl(artifact_dir / "spec_validation.jsonl")
    h_candidate_pool = load_optional_jsonl(artifact_dir / "h_candidate_pool.jsonl")
    summary = load_json(artifact_dir / "method_summary.json")

    geometry_e_rows = [row for row in variants if row["spec_id"] == "aime2024_ii_10_vera_e"]
    extra_e_rows = [
        row
        for row in variants
        if row["spec_id"] in {"aime2024_ii_9_chip_grid_vera_e", "aime2024_i_11_polygon_rotation_vera_e"}
    ]
    h_rows = [row for row in variants if row["spec_id"] == "aime2024_ii_10_vera_h"]
    h_valid_flags = [answer_valid(row) for row in h_rows]

    geometry_base_rows = [row for row in base_rows if row["spec_id"] == "aime2024_ii_10_vera_e"]
    extra_base_rows = [
        row
        for row in base_rows
        if row["spec_id"] in {"aime2024_ii_9_chip_grid_vera_e", "aime2024_i_11_polygon_rotation_vera_e"}
    ]
    seed_answers = {
        row["spec_id"]: float(row["numeric_answer"])
        for row in base_rows
        if row.get("numeric_answer") is not None and base_check_valid(row)
    }
    geometry_seed_consistency = mean(float(base_check_valid(row)) for row in geometry_base_rows) if geometry_base_rows else 0.0
    extra_seed_consistency = mean(float(base_check_valid(row)) for row in extra_base_rows) if extra_base_rows else 0.0
    geometry_replay = mean(
        float(replay_match(row)) for row in replay_rows if row["spec_id"] == "aime2024_ii_10_vera_e"
    )
    extra_replay_rows = [
        row
        for row in replay_rows
        if row["spec_id"] in {"aime2024_ii_9_chip_grid_vera_e", "aime2024_i_11_polygon_rotation_vera_e"}
    ]
    extra_replay = mean(float(replay_match(row)) for row in extra_replay_rows) if extra_replay_rows else 0.0
    h_noise_judge = mean(float(noise_judge_pass(row)) for row in h_rows) if h_rows else 0.0
    geometry_valid = mean(float(answer_valid(row)) for row in geometry_e_rows) if geometry_e_rows else 0.0
    extra_valid = mean(float(answer_valid(row)) for row in extra_e_rows) if extra_e_rows else 0.0

    h_best_rank = max((h_hardness_rank(row) for row in h_rows if answer_valid(row)), default=-1)
    h_pro_selected_ranked = (
        1.0 if h_pro_rows and h_hardness_rank(h_pro_rows[0]) == h_best_rank and answer_valid(h_pro_rows[0]) else 0.0
    )
    h_pool_best_rank = max((h_hardness_rank(row) for row in h_candidate_pool if answer_valid(row)), default=-1)
    h_pro_selected_from_valid_pool = (
        1.0
        if h_pro_rows
        and h_candidate_pool
        and h_hardness_rank(h_pro_rows[0]) == h_pool_best_rank
        and answer_valid(h_pro_rows[0])
        else 0.0
    )
    summary_h_pro = summary.get("h_pro_selected") or {}
    if summary_h_pro and h_pro_rows and summary_h_pro.get("variant_id") != h_pro_rows[0].get("variant_id"):
        raise ValueError("method_summary.json and vera_h_pro.jsonl disagree on selected H-Pro variant")

    scores = {
        "experiments": {
            "aime_geometry_vera_e_generation": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(answer_valid(row)) for row in geometry_e_rows),
                        "seed_consistency_rate": geometry_seed_consistency,
                        "valid_rate": geometry_valid,
                        "valid_assignment_diversity_rate": valid_assignment_diversity_rate(geometry_e_rows),
                        "valid_seed_answer_novelty_rate": valid_seed_answer_novelty_rate(
                            geometry_e_rows, seed_answers
                        ),
                        "validation_gate_pass_rate": validation_gate_pass_rate(
                            validation_rows, {"aime2024_ii_10_vera_e"}
                        ),
                        "deterministic_replay_rate": geometry_replay,
                    }
                }
            },
            "aime_additional_vera_e_generation": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(answer_valid(row)) for row in extra_e_rows),
                        "seed_consistency_rate": extra_seed_consistency,
                        "valid_rate": extra_valid,
                        "valid_assignment_diversity_rate": valid_assignment_diversity_rate(extra_e_rows),
                        "valid_seed_answer_novelty_rate": valid_seed_answer_novelty_rate(extra_e_rows, seed_answers),
                        "valid_spec_coverage_rate": valid_spec_coverage_rate(
                            extra_e_rows,
                            {"aime2024_ii_9_chip_grid_vera_e", "aime2024_i_11_polygon_rotation_vera_e"},
                        ),
                        "validation_gate_pass_rate": validation_gate_pass_rate(
                            validation_rows,
                            {"aime2024_ii_9_chip_grid_vera_e", "aime2024_i_11_polygon_rotation_vera_e"},
                        ),
                        "deterministic_replay_rate": extra_replay,
                    }
                }
            },
            "aime_geometry_vera_h_hardening": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(flag) for flag in h_valid_flags),
                        "noise_judge_pass_rate": h_noise_judge,
                        "valid_assignment_diversity_rate": valid_assignment_diversity_rate(h_rows),
                        "valid_seed_answer_novelty_rate": valid_seed_answer_novelty_rate(h_rows, seed_answers),
                        "valid_hardness_diversity_rate": valid_hardness_diversity_rate(h_rows),
                        "valid_mean_hardness_rank_rate": valid_mean_hardness_rank_rate(h_rows),
                        "validation_gate_pass_rate": validation_gate_pass_rate(
                            validation_rows, {"aime2024_ii_10_vera_h"}
                        ),
                        "h_candidate_pool_valid_rate": h_candidate_pool_valid_rate(h_candidate_pool),
                        "h_pro_selected_from_valid_pool": h_pro_selected_from_valid_pool,
                        "h_pro_selected_ranked": h_pro_selected_ranked,
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
