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
and hardened variants for renewed difficulty.

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

VeRA-E keeps the seed semantics fixed and accepts a specification only when the
verifier reproduces the seed answer. VeRA-H changes the task to make it harder
while keeping labels verifier-certified. VeRA-H Pro selects the hardest verified
candidate from a fixed hardened candidate pool.

This reproduction clones the upstream release in `method/VeRA` and adds a small
offline implementation in `method/vera_repro`. The released live Teacher, Judge,
and Student hooks require private endpoints, so the runnable experiment uses
the paper's AIME-2024-II-10 geometry specification family directly while
preserving the core executable-specification computation.

## Main Claims

The primary claim reproduced here is that executable specifications can produce
fresh, verifier-labeled variants at near-zero marginal cost while preserving
label integrity. A secondary reproduced claim is that hardened variants can be
selected from verified candidates under a paired VeRA-H Pro protocol.

---

# Evaluation

Evaluation reads generated artifacts from `outputs/vera_repro/`; it does not
import from `method/`. The evaluator independently recomputes geometry labels
from the emitted slot assignments, checks replay pairs, and verifies that the
H-Pro artifact is the maximum-answer verified hardened candidate.

## Metrics

- `seed_consistency_rate`: fraction of base assignments that reproduce the known
  seed answer. Higher is better.
- `valid_rate`: fraction of generated assignments accepted by the verifier.
  Higher is better.
- `deterministic_replay_rate`: fraction of variants exactly reproduced from the
  same identifiers. Higher is better.
- `noise_judge_pass_rate`: fraction of answer-noise checks that distinguish the
  verifier label from nearby incorrect labels. Higher is better.
- `paper_example_answer_abs_error`: absolute error on the paper's shown hardened
  geometry example. Lower is better.

## Baselines and Targets

The reference target is perfect seed consistency, valid generation,
deterministic replay, and label validation on the geometry family used in the
paper's AIME-2024-II-10 running example.

## Evaluation Protocol

Run `bash scripts/reproduce.sh`, which generates artifacts and then calls
`scripts/evaluate.sh`. The evaluator writes `scoring/scores.json` using the
same experiment names as `scoring/reference.json`. Standalone evaluation expects
`variants.jsonl`, `replay_checks.jsonl`, `vera_h_pro.jsonl`, and
`method_summary.json` under the artifact directory.

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


---

# Reproduction Milestones

**Current: method_runs**

## Stop Justification
- Completed at milestone `method_runs`.
