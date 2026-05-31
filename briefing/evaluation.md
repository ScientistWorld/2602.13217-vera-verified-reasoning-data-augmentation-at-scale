# Evaluation

Evaluation reads generated artifacts from `outputs/vera_repro/`; it does not
import from `method/`. The evaluator independently recomputes labels from the
emitted slot assignments, checks replay pairs, and verifies that the H-Pro
artifact is the highest-ranked verified hardened candidate under a fixed
selection rule.

## Metrics

- `seed_consistency_rate`: fraction of base assignments that reproduce the known
  seed answer. Higher is better.
- `valid_rate`: fraction of generated assignments accepted by the verifier.
  Higher is better.
- `deterministic_replay_rate`: fraction of variants exactly reproduced from the
  same identifiers. Higher is better.
- `noise_judge_pass_rate`: fraction of answer-noise checks that distinguish the
  verifier label from nearby incorrect labels. Higher is better.
- `h_pro_selected_ranked`: whether the paired H-Pro output is the highest-ranked
  verified candidate. Higher is better.
- `paper_example_answer_abs_error`: absolute error on the paper's shown hardened
  geometry example. Lower is better.

## Baselines and Targets

The reference target is perfect seed consistency, valid generation,
deterministic replay, and label validation on the geometry family used in the
paper's AIME-2024-II-10 running example, plus two additional paper-shown
VeRA-E families.

## Evaluation Protocol

Run `bash scripts/reproduce.sh`, which generates artifacts and then calls
`scripts/evaluate.sh`. The evaluator writes `scoring/scores.json` using the
same experiment names as `scoring/reference.json`. Standalone evaluation expects
`base_checks.jsonl`, `variants.jsonl`, `replay_checks.jsonl`,
`vera_h_pro.jsonl`, and `method_summary.json` under the artifact directory.
