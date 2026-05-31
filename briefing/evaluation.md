# Evaluation

Evaluation reads generated artifacts from `outputs/vera_repro/`; it does not
import from `method/`. Each artifact must contain generated variants with a
question, slot assignment, mode, and numeric answer.

## Metrics

- `seed_consistency_rate`: fraction of base assignments that reproduce the known
  seed answer. Higher is better.
- `valid_rate`: fraction of generated assignments accepted by the verifier.
  Higher is better.
- `deterministic_replay_rate`: fraction of variants exactly reproduced from the
  same identifiers. Higher is better.
- `noise_judge_pass_rate`: fraction of answer-noise checks that distinguish the
  verifier label from nearby incorrect labels. Higher is better.
- `paper_example_answer_abs_error`: absolute error on the paper's shown hardened
  geometry example. Lower is better.

## Baselines and Targets

The reference target is perfect seed consistency, valid generation,
deterministic replay, and label validation on the geometry family used in the
paper's AIME-2024-II-10 running example.

## Evaluation Protocol

Run `bash scripts/reproduce.sh`, which generates artifacts and then calls
`scripts/evaluate.sh`. The evaluator writes `scoring/scores.json` using the
same experiment names as `scoring/reference.json`.
