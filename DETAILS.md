# Overview

- **Paper ID:** 2602.13217
- **Title:** VeRA: Verified Reasoning Data Augmentation at Scale
- **Domain:** Reasoning benchmark generation and evaluation
- **TL;DR:** VeRA turns static benchmark questions into executable families
  (template, generator, verifier) that generate fresh verified variants.

## Short Summary

Static reasoning benchmarks invite memorization and lose discriminative power.
VeRA compiles a seed problem into an executable specification so new variants
can be sampled and labeled deterministically, with specifications validated
(seed consistency for equivalent families) before their labels are trusted.
This gym measures the VeRA-E synthesis step on GSM8K seeds: a hidden evaluator
runs each submitted specification on secret keys and checks every label
against the seed's latent calculation.

## Key Results (paper)

- GSM8K: 1319/1319 seeds compile into accepted VeRA-E specifications on the
  first try with a frontier Teacher (Table 1); verified rewrites reduce the
  both-models-wrong artifact proxy from 2.12% to 0.76%.
- AIME-2024: VeRA-E lowers the 16-model mean Avg@5 from 84.46% to 70.25%.
- AIME-2024-II: VeRA-H Pro lowers the mean Avg@5 from 84.91% to 58.57%.

## This gym

Reference: the paper's synthesis loop with a local Qwen2.5-7B-Instruct
Teacher. Scores are in `scoring/scores_test.json` (hidden test) and
`scoring/scores_train.json`; see `briefing/evaluation.md` for the protocol.

---

# Problem Definition

Static reasoning benchmarks become less useful when their items are reused,
memorized, or saturated. The problem is to turn each fixed reasoning seed into
a renewable *family* of fresh benchmark items whose labels can be trusted
without per-item human annotation or model-voting agreement.

## Task in this gym

For each seed problem (a GSM8K-style math word problem with its final answer,
and a fixed list of the numbers written in it, called slots) produce an
executable specification:

- a **template**: the question with every slot replaced by a placeholder,
- a **generator**: code that, given a random-number generator, returns new
  values for all slots,
- a **verifier**: code that, given slot values, decides whether they form a
  valid instance and returns its answer.

Sampling the generator, rendering the template and running the verifier must
yield fresh questions whose answers are correct, i.e. equal to what the seed's
own underlying calculation gives for the new numbers. The seed values must
still reproduce the seed answer.

## Research Question

How many seeds can be turned into trustworthy renewable families, and how can
one avoid families that look right at the seed but silently mislabel the fresh
items they generate?

## Why It Matters

A renewable family that emits wrong labels is worse than no family: every
instance it generates carries the error. Useful renewal therefore needs both
coverage (many seeds become families with many fresh items) and label
integrity (families with wrong labels are rare).

## Success Criteria

High coverage of seeds by families whose fresh variants are correctly labeled,
deterministically reproducible from their sampling key, and vary every number
of the question; few families that emit any wrong label.

---

# Paper's Method

## Key Contribution

VeRA represents benchmark items as executable specifications (template,
generator, verifier) that generate fresh verified variants on demand, so the
scale of evaluation is decoupled from the cost of labeling each item.

## Approach (paper Sections 3.1-3.5, Algorithm 1)

A Teacher LLM compiles a seed `(question, answer)` into a candidate
specification. Each candidate passes validation gates before its correctness is
amortized over all samples: (1) schema parse, (2) sandbox compilation,
(3) runtime on a batch of hash-seeded samples, (4) non-degenerate yield, and
(5) the mode-specific check — for VeRA-E, seed-anchored consistency
`V(theta_seed) == (True, a)`. Failures become structured feedback and the
Teacher retries (20 attempts per seed). Accepted specs are sampled with
`seed = Hash(seed_id, generator_id, sample_idx)`; code runs in a restricted
sandbox. VeRA-H (hardened families) and VeRA-H Pro additionally use a Judge
model; they are not part of this gym because hardened tasks have no external
ground truth to hold a hidden test against.

## This reproduction (`method/vera/`)

- Seeds: GSM8K problems (the paper's GSM8K VeRA-E setting), with a fixed slot
  schema (every digit-written number) so the hidden test can check labels.
- Teacher: local `Qwen2.5-7B-Instruct` (the paper uses frontier models);
  greedy first attempt, temperature 0.7 for retries; up to 20 attempts per seed
  with the paper's feedback loop. The Teacher sees the question and the final
  answer (as for the paper's AIME seeds), not the worked solution.
- Gates: schema, compile, runtime on 20 hash-seeded samples, sampler yield
  (generator retried until the verifier accepts; >= 50% accepted and >= 2
  distinct fresh assignments), and seed consistency.
- Sandbox: restricted builtins, import whitelist, per-call timers, resource
  limits (`method/vera/sandbox.py`, `sandbox_worker.py`).
- Output: `outputs/vera_e/specs.jsonl` (reference). `scripts/method.sh` with
  `VARIANTS_OUT=<dir>` also writes comparison variants: `vera_e_1try` (first
  attempt only), `vera_e_seed1` (different retry sampling seed, a noise
  estimate) and `vera_e_xcheck` (adds an instance-level cross-check against an
  independently derived `solve()` program, the randomized fuzzing the paper
  recommends in Section 5.2).

## Main Claims

Executable specifications produce fresh, verifier-labeled variants at
near-zero marginal cost while preserving label integrity, and the
validate-and-retry synthesis loop raises how many seeds compile into accepted
specifications (Table 1: one try vs. up to 20 tries). With a 7B Teacher the
seed-consistency gate is not sufficient: a sizeable share of accepted
specifications mislabel fresh variants, which is where this gym has headroom.

---

# Evaluation

## Data

- `data/gsm8k_vera/train_seeds.jsonl` (221 seeds) and
  `data/gsm8k_vera/test_seeds.jsonl` (627 seeds): `seed_id`, `question`,
  `answer` (a non-negative integer), and `slots` — one per number written with
  digits in the question: `name` (`n0`, `n1`, ...), `text`, `value`, `kind`
  (`int` or `float`), and character offsets `start` / `end`.
- Train seeds also carry the worked GSM8K `solution`, and
  `eval/train/references.jsonl` holds the train reference programs (the
  seed's calculation as a list of arithmetic steps over the slots). Test seeds
  carry neither; their references are hidden.
- Seeds are GSM8K problems with at least three calculation steps whose
  reference program could be recovered unambiguously from the official
  calculator annotations.

## Submission

Each method writes `outputs/<method>/specs.jsonl`, one JSON object per seed:

```json
{"seed_id": "te0001", "template": "... {n0} ... {n1} ...",
 "generator_code": "def generator(rng): ...  # returns {'n0': ..., 'n1': ...}",
 "verifier_code": "def verifier(assign): ...  # returns (True, answer) or (False, None)"}
```

Every directory under `outputs/` is scored as a method, whatever its name; a
directory without a readable `specs.jsonl`, or with a duplicated `seed_id`,
is a failed run. A seed without a row scores zero. Nothing else a method writes
is read.

Code rules (checked statically and enforced at run time in a subprocess):
Python only; imports limited to `math`, `random`, `fractions`, `itertools`,
`functools`; no names or attributes starting with an underscore (`__` in names
or strings), no `eval/exec/open/getattr/type/...`, no classes, at most 20000
characters per field. `rng` offers `random, uniform, randint, randrange,
choice, choices, sample, shuffle, gauss, triangular`. Each call has a 2-second
timer; the process has 60 CPU-seconds, 1 GB of memory, and no file access.
Template placeholders must be exactly the seed's slot names in plain `{name}`
form (no format specs), the template at most 4000 characters.

## Protocol per seed

The evaluator executes the submitted code itself; it never reads a label or
flag the method wrote.

1. The verifier is called on the seed's slot values.
2. The generator is called with 8 secret keys (`random` is also seeded with the
   key). Each sample is replayed in an independent namespace with the keys
   walked in reverse order; a sample must depend only on its key.
3. A sample is **fresh** if its slot values differ from the seed values (int
   slots must be integers, all values positive and at most 1e9).
4. For each fresh sample the verifier accepts, the label is compared with the
   hidden reference program evaluated on the same values. The reference
   accepts an assignment only if no step divides by zero, every intermediate
   quantity is non-negative, and the final answer is a non-negative integer;
   a verifier that accepts an assignment the reference rejects, or returns a
   different value, has given a **wrong label**.
5. A fresh sample is **counted** if its label is correct, it replays exactly,
   and the template renders it into a question containing every slot value
   (at least a quarter of the seed question's length).
6. The seed is **certified** if the verifier returns the seed answer at the
   seed values, no accepted fresh sample has a wrong label, at least one
   sample is counted, and every slot takes a non-seed value in some counted
   sample. It is **mislabeled** if any accepted fresh sample has a wrong label.

## Metrics (per experiment, averaged over all its seeds)

| Metric | Direction | Meaning |
|---|---|---|
| `verified_fresh_yield` (primary) | higher | mean over seeds of (distinct counted samples / 8) for certified seeds, 0 otherwise |
| `certified_spec_rate` | higher | fraction of seeds certified |
| `mislabeled_spec_rate` | lower | fraction of seeds mislabeled |
| `label_precision` | higher (unweighted) | correct / accepted fresh samples, pooled |
| `seed_consistency_rate` | higher (unweighted) | fraction of seeds whose verifier returns the seed answer and accepts a fresh sample |

**Failure.** If the pooled `label_precision` over all seeds is below 0.7, or
the submission is unreadable, the method fails: every metric of every
experiment gets its worst value (0, and 1.0 for `mislabeled_spec_rate`).

## Experiments

- `gsm8k_vera_e_3step` — seeds whose reference program has 3 steps
  (403 test / 142 train seeds), weight 0.5.
- `gsm8k_vera_e_multistep` — seeds with 4 or more steps (224 test / 79 train
  seeds), weight 0.5.

## Running

- `bash scripts/evaluate_train.sh` scores every directory under `outputs/` on
  the train seeds with public keys and writes `scoring/scores_train.json`
  (`scripts/evaluate.sh` writes the same numbers to `scoring/scores.json`).
- `bash scripts/evaluate_test.sh` (no arguments) scores every directory under
  `outputs/` on the hidden test seeds with secret keys and writes
  `scoring/scores_test.json`.

## Baselines

- `label_copy`: perturbs the numbers but keeps the seed answer as every
  label (unverified surface perturbation). Fails the precision floor.
- `expression_search`: brute-force search for an arithmetic expression over
  the slots that reproduces the seed answer. Coincidental matches mislabel
  fresh variants; fails the precision floor.

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

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 30m | **GPU**: 1.9h
- **Jobs**: 3 total (1 completed, 1 failed)

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

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
