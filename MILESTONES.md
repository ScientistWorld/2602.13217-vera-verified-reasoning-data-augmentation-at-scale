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

### [2026-05-31 06:28] - core_claim_plus
- Reactivation audit used a subagent to re-extract the paper's executable-specification workflow and metric requirements from Sections 3 and 4.
- Confirmed the current code implements VeRA's actual computation rather than a surrogate: sandboxed template/generator/verifier specs, seed-consistency validation, noise-discrimination validation, deterministic replay, independent evaluator label recomputation, and H-Pro selection from a verified candidate pool.
- Reran `bash scripts/reproduce.sh` and `python validate.py --compare` locally; all checks passed with refreshed `scoring/scores.json`.

### [2026-05-31 06:32] - core_claim_plus
- Final verification reviewed folder structure, download portability, shared-path hygiene, method/eval separation, scoring weights and coefficients, and train/test evaluator behavior.
- Tightened method-agnostic documentation in evaluation and scoring overview files for from-scratch scientist use.
- Reran `bash scripts/evaluate.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all checks passed.

### [2026-11-14] - core_claim_plus
- Hardening (iteration 11): the gym now measures the paper's VeRA-E synthesis
  loop on GSM8K seeds against hidden latent programs. The previous AIME gym was
  replaced because its evaluator trusted method artifacts.
- The reference (Qwen2.5-7B Teacher, paper's gates, up to 20 attempts) scores
  verified_fresh_yield 0.631 / 0.457 on the hidden test. Retries raise
  certified specs (1 try → 20 tries: 0.422 → 0.648, 0.286 → 0.469), the
  paper's Table 1 direction. A cross-checked variant scores 0.800 / 0.696.
- Closed shortcuts: key-blind generators, held-fixed slots, speculative
  low-precision fill, hidden failed methods, the leaked VeRA release data,
  and sandbox file reads. Details in `HARDENING.md`.

## Stop Justification
- Completed at milestone `core_claim_plus`.
