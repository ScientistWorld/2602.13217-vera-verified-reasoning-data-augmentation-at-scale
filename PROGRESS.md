# Progress

## What Works

- Read the paper and identified VeRA's core executable-specification pipeline:
  template, generator, verifier, deterministic hash seeding, mode-specific
  validation, and VeRA-H Pro candidate selection.
- Checked the public code release and cloned it during development. The release
  includes source code, CSV datasets, and generator artifacts, but live
  Teacher/Judge/Student hooks point to private endpoints.
- Implemented an offline reproduction in `method/vera_repro` for the
  AIME-2024-II-10 geometry family shown in the paper.
- `bash scripts/reproduce.sh` runs end-to-end locally and writes
  `scoring/scores.json`.

## Results

- VeRA-E geometry reproduction generated 8 verified variants with seed
  consistency 1.0, valid rate 1.0, and deterministic replay rate 1.0.
- VeRA-H geometry reproduction generated 8 verified hardened variants with
  noise-judge pass rate 1.0.
- VeRA-H Pro selected the paper's hardest shown geometry candidate
  `R=38, r=10, theta=75`, producing answer `2755.941038021204`; the absolute
  difference from the paper's displayed value is about `1.2e-9`.

## Remaining

- Run the packaged reproduction inside the scheduler-managed container.
- Higher milestones would require broader coverage across the released VeRA
  datasets and a local open model or accessible evaluator for Avg@5 model
  scores.

## Issues

- The upstream release's online LLM hooks are not directly runnable because they
  depend on private endpoints. The runnable reproduction therefore focuses on
  the executable-specification mechanics and a paper-shown geometry family.

## Deviations from Paper

- Paper used frontier LLM Teacher/Judge/Student services for large-scale
  synthesis and model evaluation. This reproduction uses the paper's shown
  geometry executable family directly and an offline deterministic noise checker
  for the validation role because paid/private endpoints are not available.
- Paper reports large benchmark suites. This reproduction scales down to one
  seed family while preserving the procedure: generate assignments, execute
  verifiers, validate labels, replay deterministically, and select VeRA-H Pro.
