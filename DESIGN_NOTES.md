# Train/Test Evaluation Design Notes

## Checks performed

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. The train wrapper calls `eval/train/evaluate.py` and writes `scoring/scores_train.json`; the test wrapper calls `eval/test/evaluate.py`, reads the method list from `scoring/scores_train.json`, and writes `scoring/scores_test.json`.
- Checked for hardcoded method defaults in the train/test wrappers. The split evaluators discover complete artifact directories under `outputs/` or explicit `ARTIFACT_DIR` paths and iterate over method names.
- Checked for cross-import leakage between `eval/train/` and `eval/test/`. The slice evaluators are duplicated rather than importing from each other.
- Checked that `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n scripts/evaluate_train.sh` and `bash -n scripts/evaluate_test.sh`; both passed.

## Changes made

- Removed the nonzero paper-agreement metric `paper_example_answer_abs_error` from `scoring/reference.json`. It rewarded matching a paper example rather than improving the scientific quantity.
- Added required metric descriptions for all train/test metrics in `scoring/reference.json`.
- Added `valid_assignment_diversity_rate` to the geometry VeRA-E, additional VeRA-E, and VeRA-H slice evaluators. This penalizes methods that duplicate a small set of known-valid assignments while still passing validity checks.
- Added `valid_spec_coverage_rate` for the additional VeRA-E experiment. This catches methods that optimize only one of the two visible additional specifications.
- Added `valid_hardness_diversity_rate` for the VeRA-H experiment. This rewards coverage of distinct valid difficulty ranks rather than repeated easy hardened variants.
- Implemented the same new metrics in both `eval/train/evaluate.py` and `eval/test/evaluate.py` so train and held-out test remain comparable.

## Runtime concerns for the runner iteration

- The split is still an odd/even split over method-produced `sample_index` values. It is lightweight and matches the current artifact contract, but it is not as strong as a fully hidden resampling seed because the artifact already contains all variants.
- `noise_judge_pass_rate` is an offline checker over generated numeric answers and nearby perturbations, not a real model-judge artifact. It is useful as a validity-adjacent constraint but may saturate when `valid_rate` saturates.
- The legacy top-level `eval/evaluate_vera_outputs.py` and existing `scoring/scores.json` were also aligned to stop emitting `paper_example_answer_abs_error`, because full-workspace validation checks the unsplit score file against `scoring/reference.json`.
