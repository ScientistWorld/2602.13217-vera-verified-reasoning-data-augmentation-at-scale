# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-05-31 05:44] - core_claim
- Implemented the paper's executable specification computation for the paper-shown AIME-2024-II-10 geometry family.
- Verified deterministic generation, seed consistency, verifier label integrity, replay, and VeRA-H Pro selection.
- Scheduler job `1e1b5dd0-1ee` ran `scripts/run.sh` successfully inside the container.

### [2026-05-31 05:44] - core_claim
- Expanded the local implementation to two additional paper-shown VeRA-E families: AIME-2024-II-9 chip-grid counting and AIME-2024-I-11 polygon rotation.
- Updated evaluation to recompute labels independently for all three families and to check base seed consistency from method artifacts.
- Local `bash scripts/reproduce.sh` and `python validate.py --compare` pass; a scheduler job is being submitted to confirm the expanded suite in the container before claiming `core_claim_plus`.

### [2026-05-31 05:49] - core_claim
- Continuing-agent audit found the active implementation is a real VeRA executable-specification reproduction, not a surrogate.
- Fixed the executable-spec sandbox to use restricted builtins and a math-only import hook instead of exposing full Python builtins.
- Re-ran `bash scripts/reproduce.sh`, negative sandbox checks, and `python validate.py --compare` locally; all passed.

### [2026-05-31 05:51] - core_claim_plus
- Scheduler job `67ba94e2-6fe` ran the hardened, expanded reproduction successfully inside the container with exit code 0.
- Confirmed three scored experiments: the original AIME-2024-II-10 geometry VeRA-E family, two additional paper-shown VeRA-E families, and the AIME-2024-II-10 VeRA-H/H-Pro family.
- Reproduced perfect seed consistency, valid generation, deterministic replay, noise-check pass rate, and ranked H-Pro selection on the packaged benchmark.

### [2026-05-31 06:20] - core_claim_plus
- Added explicit pre-amortization validation artifacts for schema, compile/runtime, non-degenerate yield, VeRA-E seed consistency, and VeRA-H noise discrimination gates.
- Added an emitted H-Pro candidate-pool artifact and evaluator checks that the selected H-Pro row comes from the valid pool.
- Local `bash scripts/reproduce.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare` pass; submitting a CPU scheduler job to verify these tightened artifacts in-container.

### [2026-05-31 06:23] - core_claim_plus
- Final verification found the milestone justified for a reduced offline gym: the method implements generator/verifier task families, deterministic replay, label recomputation, validation gates, and hard-case selection on three paper-shown reasoning families.
- Cleaned method-agnostic evaluation documentation and extended train/test evaluators so held-out scoring also checks validation-gate and candidate-pool artifacts.
- Re-ran `bash scripts/reproduce.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all checks passed.

## Stop Justification
- Completed at milestone `core_claim_plus`.
