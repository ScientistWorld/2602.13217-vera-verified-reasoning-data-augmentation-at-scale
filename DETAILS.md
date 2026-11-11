# Overview

- **Paper ID:** 2602.13217
- **Title:** VeRA: Verified Reasoning Data Augmentation at Scale
- **Domain:** Reasoning benchmark generation and evaluation
- **TL;DR:** VeRA turns static benchmark questions into executable families
  that generate fresh verified variants.

## Short Summary

The paper argues that static reasoning benchmarks invite memorization and lose
discriminative power as models improve. VeRA compiles a seed problem into a
template, generator, and verifier so new variants can be sampled and labeled
deterministically. It supports equivalent rewrites for robustness diagnostics
and hardened variants for renewed difficulty. This workspace reproduces those
mechanics offline on paper-shown AIME executable families.

## Key Results

- GSM8K verified rewrites reduce the paper's conservative both-wrong artifact
  proxy from 2.12% to 0.76%.
- On AIME-2024, VeRA-E lowers the 16-model mean Avg@5 from 84.46% to 70.25%,
  exposing brittleness under verified equivalent variants.
- On AIME-2024-II, VeRA-H Pro lowers the mean Avg@5 from 84.91% to 58.57%,
  restoring headroom with verifier-certified labels.

---

# Problem Definition

Static reasoning benchmarks become less useful when their items are repeatedly
reused, memorized, or saturated. The problem is to turn a fixed reasoning seed
into a renewable family of fresh benchmark items with reliable labels.

## Research Question

Can a benchmark item be transformed into many new, valid reasoning questions
whose labels remain trustworthy without requiring per-item human annotation or
model-voting agreement?

## Why It Matters

Renewable benchmark families make it harder to exploit memorized static answers
and keep evaluation useful after a finite benchmark saturates.

## Success Criteria

A successful system produces fresh question instances, labels them
deterministically, reproduces the known seed answer, and can replay the same
instance from the same immutable identifiers.

---

# Paper's Method

## Key Contribution

VeRA represents benchmark items as executable specifications that can generate
fresh verified variants on demand. This separates benchmark scale from the cost
of relabeling every item.

## Approach

Each specification contains a natural-language template, a deterministic
generator for valid slot assignments, and a deterministic verifier that checks
the assignment and computes the canonical answer. Sampling uses a hash of
immutable identifiers, so variants are reproducible.
Generator and verifier snippets are executed in a restricted sandbox with
deterministic builtins and math-only imports.

VeRA-E keeps the seed semantics fixed and accepts a specification only when the
verifier reproduces the seed answer. VeRA-H changes the task to make it harder
while keeping labels verifier-certified. VeRA-H Pro selects the hardest verified
candidate from a fixed hardened candidate pool.

This reproduction clones the upstream release in `method/VeRA` and adds a small
offline implementation in `method/vera_repro`. The released live Teacher, Judge,
and Student hooks require private endpoints, so the runnable experiment uses
paper-shown AIME executable families directly: the AIME-2024-II-10 geometry
family, the AIME-2024-II-9 chip-grid family, and the AIME-2024-I-11
polygon-rotation family. The reproduction preserves the core
executable-specification computation.

## Main Claims

The primary claim reproduced here is that executable specifications can produce
fresh, verifier-labeled variants at near-zero marginal cost while preserving
label integrity. A secondary reproduced claim is that hardened variants can be
selected from verified candidates under a paired VeRA-H Pro protocol.

---

# Evaluation

Evaluation reads generated artifacts from a configured artifact directory and
does not import from any solution implementation. The evaluator independently
recomputes labels from submitted structured assignments, checks replay pairs,
and verifies that the selected hard-case artifact is drawn from the submitted
eligible candidate pool under a fixed selection rule.

## Metrics

- `seed_consistency_rate`: fraction of base assignments that reproduce the known
  seed answer. Higher is better.
- `valid_rate`: fraction of generated assignments accepted by independent
  checks.
  Higher is better.
- `deterministic_replay_rate`: fraction of variants exactly reproduced from the
  same identifiers. Higher is better.
- `noise_judge_pass_rate`: fraction of answer-noise checks that distinguish the
  submitted label from nearby incorrect labels. Higher is better.
- `validation_gate_pass_rate`: fraction of expected task-artifact definitions
  that pass schema, compile/runtime, yield, and mode-specific validation gates
  before repeated sampling. Higher is better.
- `h_candidate_pool_valid_rate`: fraction of hard-case candidate-pool rows that
  remain valid under independent evaluator recomputation. Higher is better.
- `h_pro_selected_from_valid_pool`: whether the paired hard-case output is
  selected from the emitted valid candidate pool. Higher is better.
- `h_pro_selected_ranked`: whether the paired hard-case output is the
  highest-ranked verified candidate. Higher is better.

## Baselines and Targets

The reference target is perfect seed consistency, valid generation,
deterministic replay, and label validation on one geometry seed family, plus
two additional reasoning seed families.

## Evaluation Protocol

Run `bash scripts/reproduce.sh`, which generates artifacts and then calls
`scripts/evaluate.sh`. The evaluator writes `scoring/scores.json` using the
same experiment names as `scoring/reference.json`. Standalone evaluation expects
`base_checks.jsonl`, `variants.jsonl`, `replay_checks.jsonl`,
`spec_validation.jsonl`, `h_candidate_pool.jsonl`, `vera_h_pro.jsonl`, and
`method_summary.json` under the artifact directory. Set `ARTIFACT_DIR` to score
artifacts produced by another method.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

<!-- Write your progress here -->

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 14m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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
- Scheduler job `1e1b5dd0-1ee` completed with exit code 0 and reproduced the
  same score artifacts inside the container.

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 13m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

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

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
