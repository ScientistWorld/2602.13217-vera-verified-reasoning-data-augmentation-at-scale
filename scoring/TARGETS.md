# Evaluation Targets

Both experiments are scored on the hidden test split by
`bash scripts/evaluate_test.sh` (no arguments; every directory under
`outputs/` is a method) and on the visible train split by
`bash scripts/evaluate_train.sh`. Experiment weights: 0.5 each.

## Primary: gsm8k_vera_e_3step

Renewable verified families for seeds whose calculation has three steps.

- **Primary metric**: `verified_fresh_yield` (higher is better, coefficient 1.0)
- **Benefit metric**: `certified_spec_rate` (higher is better, coefficient 0.5)
- **Constraint metric**: `mislabeled_spec_rate` (lower is better,
  coefficient 1.0); pooled `label_precision` below 0.7 fails the run
- **Diagnostics (coefficient 0)**: `label_precision`, `seed_consistency_rate`

## Primary: gsm8k_vera_e_multistep

The same targets for seeds whose calculation has four or more steps.

- **Primary metric**: `verified_fresh_yield` (higher is better, coefficient 1.0)
- **Benefit metric**: `certified_spec_rate` (higher is better, coefficient 0.5)
- **Constraint metric**: `mislabeled_spec_rate` (lower is better,
  coefficient 1.0); pooled `label_precision` below 0.7 fails the run
- **Diagnostics (coefficient 0)**: `label_precision`, `seed_consistency_rate`

## Reference and baselines

`scoring/reference.json` holds this gym's reference run (`vera_e`) and the
baselines (`label_copy`, `expression_search`, both failing the precision
floor), plus the paper's own GSM8K numbers under `_paper_reported` (not on
this gym's scale).
