# Evaluation

Evaluation reads generated artifacts from a configured artifact directory and
does not import from any solution implementation. The evaluator independently
recomputes labels from submitted structured assignments, checks replay pairs,
and verifies that the selected hard-case artifact is drawn from the submitted
eligible candidate pool under a fixed selection rule.

## Metrics

- `seed_consistency_rate`: fraction of base assignments that reproduce the known
  seed answer. Higher is better.
- `valid_rate`: fraction of generated assignments accepted by independent
  checks.
  Higher is better.
- `deterministic_replay_rate`: fraction of variants exactly reproduced from the
  same identifiers. Higher is better.
- `noise_judge_pass_rate`: fraction of answer-noise checks that distinguish the
  submitted label from nearby incorrect labels. Higher is better.
- `validation_gate_pass_rate`: fraction of expected task-artifact definitions
  that pass schema, compile/runtime, yield, and mode-specific validation gates
  before repeated sampling. Higher is better.
- `h_candidate_pool_valid_rate`: fraction of hard-case candidate-pool rows that
  remain valid under independent evaluator recomputation. Higher is better.
- `h_pro_selected_from_valid_pool`: whether the paired hard-case output is
  selected from the emitted valid candidate pool. Higher is better.
- `h_pro_selected_ranked`: whether the paired hard-case output is the
  highest-ranked verified candidate. Higher is better.

## Baselines and Targets

The reference target is perfect seed consistency, valid generation,
deterministic replay, and label validation on one geometry seed family, plus
two additional reasoning seed families.

## Evaluation Protocol

Run `bash scripts/reproduce.sh`, which generates artifacts and then calls
`scripts/evaluate.sh`. The evaluator writes `scoring/scores.json` using the
same experiment names as `scoring/reference.json`. Standalone evaluation expects
`base_checks.jsonl`, `variants.jsonl`, `replay_checks.jsonl`,
`spec_validation.jsonl`, `h_candidate_pool.jsonl`, `vera_h_pro.jsonl`, and
`method_summary.json` under the artifact directory. Set `ARTIFACT_DIR` to score
artifacts produced by another method.
