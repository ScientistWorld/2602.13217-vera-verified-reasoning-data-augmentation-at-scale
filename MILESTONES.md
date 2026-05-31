# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 05:35] - core_claim
- Continuing-agent audit reran `bash scripts/reproduce.sh` and `python validate.py --compare`.
- Confirmed the implementation is an executable-specification reproduction rather than a surrogate model: templates, deterministic generators, verifiers, replay, and H-Pro selection are present.
- Confirmed `eval/` independently scores method artifacts without importing from `method/`; milestone restored to `core_claim`.

### [2026-05-31 05:35] - core_claim
- Completed a scheduler job running `scripts/reproduce.sh` inside the container with exit code 0.
- Reproduced VeRA's core executable-specification claim on the AIME geometry family: generation produced valid verified variants, replay was deterministic, and evaluation independently recomputed labels from method artifacts.
- Reproduced the VeRA-H Pro selection check for the paper-shown hardened geometry candidate with near-zero answer error.

### [2026-05-31 05:32] - method_runs
- Implemented the offline VeRA executable-specification reproduction and evaluator.
- Method, reproduction script, and evaluation pipeline ran end-to-end.

## Stop Justification
- Completed at milestone `core_claim`.
