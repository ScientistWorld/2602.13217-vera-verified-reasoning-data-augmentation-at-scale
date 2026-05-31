# Evaluation Targets

## Primary: aime_geometry_vera_e_generation

Tests whether a renewable reasoning item family preserves the known seed
answer while generating replayable valid variants.

- **Primary metric**: `seed_consistency_rate` (higher is better)
- **Constraint metrics**: `valid_rate` and `deterministic_replay_rate` (higher
  is better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`

## Primary: aime_geometry_vera_h_hardening

Tests whether a harder paired variant can be selected from a pool of verified
candidates while preserving label integrity.

- **Primary metric**: `noise_judge_pass_rate` (higher is better)
- **Constraint metrics**: `h_pro_selected_ranked` (higher is better) and
  `paper_example_answer_abs_error` (lower is better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`

## Primary: aime_additional_vera_e_generation

Tests the same executable-specification evaluation on two additional
paper-shown families: chip-grid maximal placements and polygon rotation
probability.

- **Primary metric**: `seed_consistency_rate` (higher is better)
- **Constraint metrics**: `valid_rate` and `deterministic_replay_rate` (higher
  is better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`
