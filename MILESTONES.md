# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 05:20] - none
- Read the paper and identified the core executable specification algorithm.
- Inspected the public VeRA code release and its offline artifacts.

### [2026-05-31 05:20] - method_runs
- Implemented the paper's executable-specification computation for the
  AIME-2024-II-10 geometry family.
- `scripts/reproduce.sh` runs end-to-end locally and writes reproducible
  scores.

### [2026-05-31 05:47] - core_claim
- Audited the previous implementation and fixed evaluator trust in
  method-produced summary rates.
- Local reproduction and validation support VeRA's core claim on a scaled-down
  paper-shown geometry family: deterministic executable specifications produce
  verified variants and select a verified hardened candidate.

## Stop Justification

Not stopped. A scheduler job is being submitted to verify the packaged
environment after the evaluator fix.
