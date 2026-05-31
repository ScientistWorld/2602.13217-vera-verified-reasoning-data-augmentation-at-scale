from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="outputs/vera_repro")
    parser.add_argument("--scores", default="scoring/scores.json")
    args = parser.parse_args()

    artifact_dir = Path(args.artifacts)
    summary = load_json(artifact_dir / "method_summary.json")
    specs = summary["specs"]
    e_specs = [s for s in specs if s["mode"] == "VeRA-E"]
    h_specs = [s for s in specs if s["mode"] == "VeRA-H"]
    all_specs = specs

    e_seed_consistency = mean(float(s["seed_consistent"]) for s in e_specs) if e_specs else 0.0
    all_valid = mean(float(s["valid_rate"]) for s in all_specs) if all_specs else 0.0
    all_replay = mean(float(s["deterministic_replay_rate"]) for s in all_specs) if all_specs else 0.0
    all_judge = mean(float(s["noise_judge_pass_rate"]) for s in all_specs) if all_specs else 0.0
    h_reference = h_specs[0]["expected_base_answer"] if h_specs else None
    h_observed = h_specs[0]["base_answer"] if h_specs else None
    h_answer_error = abs(float(h_observed) - float(h_reference)) if h_reference is not None else 0.0
    h_pro_selected_max = 1.0 if summary.get("h_pro_selected") else 0.0

    scores = {
        "experiments": {
            "aime_geometry_vera_e_generation": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(s["generated"]) for s in e_specs),
                        "seed_consistency_rate": e_seed_consistency,
                        "valid_rate": all_valid,
                        "deterministic_replay_rate": all_replay,
                    }
                }
            },
            "aime_geometry_vera_h_hardening": {
                "results": {
                    "vera_repro": {
                        "verified_variant_count": sum(int(s["generated"]) for s in h_specs),
                        "noise_judge_pass_rate": all_judge,
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

