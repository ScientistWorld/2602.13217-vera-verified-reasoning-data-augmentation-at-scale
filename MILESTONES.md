# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 05:35] - core_claim
- Completed a scheduler job running `scripts/reproduce.sh` inside the container with exit code 0.
- Reproduced VeRA's core executable-specification claim on the AIME geometry family: generation produced valid verified variants, replay was deterministic, and evaluation independently recomputed labels from method artifacts.
- Reproduced the VeRA-H Pro selection check for the paper-shown hardened geometry candidate with near-zero answer error.

### [2026-05-31 05:32] - method_runs
- Implemented the offline VeRA executable-specification reproduction and evaluator.
- Method, reproduction script, and evaluation pipeline ran end-to-end.

## Stop Justification
- Completed at milestone `core_claim`. Higher milestones would require broader benchmark/model coverage beyond the offline geometry-family reproduction.
