# Evaluation Targets

## Primary: aime_geometry_vera_e_generation

Tests whether a renewable reasoning item family preserves the known seed
answer while generating replayable valid variants.

- **Primary metric**: `valid_seed_answer_novelty_rate` (higher is better)
- **Constraint metrics**: `seed_consistency_rate`, `valid_rate`, and
  `validation_gate_pass_rate`, and `deterministic_replay_rate` (higher is
  better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`

## Primary: aime_geometry_vera_h_hardening

Tests whether a harder paired variant can be selected from a pool of verified
candidates while preserving label integrity.

- **Primary metric**: `valid_mean_hardness_rank_rate` (higher is better)
- **Constraint metrics**: `h_pro_selected_ranked`, `valid_hardness_diversity_rate`,
  `h_pro_selected_from_valid_pool`, `h_candidate_pool_valid_rate`,
  `valid_seed_answer_novelty_rate`, `validation_gate_pass_rate`, and
  `noise_judge_pass_rate` (higher is better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`

## Primary: aime_additional_vera_e_generation

Tests the same executable-specification evaluation on two additional
paper-shown families: chip-grid maximal placements and polygon rotation
probability.

- **Primary metric**: `valid_seed_answer_novelty_rate` (higher is better)
- **Constraint metrics**: `seed_consistency_rate`, `valid_rate`, and
  `validation_gate_pass_rate`, and `deterministic_replay_rate` (higher is
  better)
- **How to run**: `bash scripts/reproduce.sh`, then inspect
  `scoring/scores.json`
