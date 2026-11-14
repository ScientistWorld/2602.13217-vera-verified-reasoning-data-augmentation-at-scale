# Train/Test Evaluation Design Notes

- `scripts/evaluate_train.sh` → `eval/train/evaluate.py` →
  `scoring/scores_train.json`; `scripts/evaluate_test.sh` →
  `eval/test/evaluate.py` → `scoring/scores_test.json`. Both take no
  arguments and score every directory under `outputs/` (a directory without a
  readable `specs.jsonl` is a failed run with worst values).
- The two evaluators are identical copies except for seeds, references and
  key salt (train keys are public, test keys secret); they share no code and
  do not import `method/`.
- The evaluator executes the submitted code itself (`sandbox_runner.py`,
  restricted builtins, import whitelist, timers, no file access) and recomputes
  every label from the hidden reference program. Replay walks keys in reverse
  in a fresh namespace, and a certified family must vary every slot.
- Scored metrics: `verified_fresh_yield` (1.0), `certified_spec_rate` (0.5),
  `mislabeled_spec_rate` (lower is better, 1.5). Diagnostics:
  `label_precision` (pooled below 0.7 fails the run), `seed_consistency_rate`.
- Hidden references are built once by `eval/test/build_split.py` from the raw
  GSM8K files; seeds with ambiguous annotation-to-slot mappings and 2-step
  seeds (solved by enumeration) are excluded.
