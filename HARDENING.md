# Hardening report (iteration 11)

## Where this gym started and what it is now

`REDTEAM.md` audited the earlier AIME gym: four hand-written families whose
evaluator trusted method-written artifacts. Fixed outputs, empty questions,
fabricated validation flags, moved seed answers and replaced H-Pro selections
all beat the reference (+0.28 to +0.33 raw), a moved seed reached every
metric's bound, the baseline was not scored, and the method package did not
even run. Earlier in this iteration that gym was replaced by one built on the
paper's own VeRA-E pipeline. This session hardened and documented the new gym.

**Task.** For each GSM8K seed (question, final answer, slot schema = every
number written with digits), submit an executable specification: template,
generator, verifier. The hidden evaluator (`eval/test/`) runs the submitted
code itself in a sandbox on secret keys and checks every label against the
seed's latent program, recovered from GSM8K's calculator annotations
(`eval/test/references.jsonl`, built by `eval/test/build_split.py`). It reads
nothing the method asserts. Seeds have at least 3 steps, because 2-step seeds
are solved by expression enumeration. Splits: 627 hidden test seeds and 221
train seeds. Experiments: `gsm8k_vera_e_3step` and `gsm8k_vera_e_multistep`
(4 or more steps), weight 0.5 each.

**Reference.** The paper's synthesis loop (Sections 3.3-3.4, Algorithm 1), run
with a local Qwen2.5-7B-Instruct Teacher. The gates are schema, compile,
runtime, sampler yield and seed consistency; failed attempts produce feedback
and the Teacher retries, now up to the paper's 20 attempts. Baselines:
`label_copy` (perturb the numbers, copy the seed label) and
`expression_search` (brute-force expression matching the seed answer).

## Changes made in this session

1. **Leak removed.** The tracked upstream clone `method/VeRA` (69 MB) shipped
   `GSM8k_VeRA-E.csv`: 20 labeled variants, made by the paper's frontier
   Teacher, for every GSM8K test problem. Most hidden test seeds are GSM8K
   test problems, so those 20 points pin down each hidden program. The clone
   was removed from git and disk; nothing imported it.
2. **Replay must depend on the key only** (`sandbox_runner.py`, train and
   test). The second replay namespace walks the keys in reverse. Before, a
   generator that ignored its key and cycled through a fixed list by call
   count passed replay, which made the secret keys meaningless.
3. **A certified family must vary every slot** (`evaluate.py`). Before, a
   generator could hold numbers at their seed values, so the hidden program
   never checked how the verifier handled them (hard-coded seed values passed).
4. **New scored constraint `mislabeled_spec_rate`**: the fraction of seeds
   whose family accepts any fresh variant with a wrong label. This is the
   analogue of the paper's label-artifact rate; lower is better, coefficient
   1.5. `label_precision` stays as the failure floor (pooled below 0.7 fails
   the run) with coefficient 0. A ratio rewards submitting fewer specs, and it
   barely registered families that emit wrong labels.
   `seed_consistency_rate` (the paper's gate) also got coefficient 0, because
   it rewards keeping seed-consistent specs that mislabel fresh variants.
5. **Every directory under `outputs/` is scored**, including names starting
   with `_` or `.`. Before, those were skipped, so a failed method could hide
   and, under skip-missing ranking, tie the reference. A crash while scoring a
   seed or a method now scores it as failed instead of aborting the whole run.
   Template placeholders must be plain `{slot}`, which also stops
   format-width memory bombs in the evaluator process.
6. **The sandbox cannot open files** (`RLIMIT_NOFILE` = 3, set after all
   imports). Checked with a runner copy that deliberately exposes `open`: the
   read of `eval/test/references.jsonl` fails.
7. **Paper setting restored**: the Teacher retry cap goes from 6 back to the
   paper's 20 (Section 4.1). The Teacher cache moved into `outputs/vera_e/`.
   The comparison variants (`vera_e_1try`, `vera_e_seed1`, `vera_e_xcheck`)
   are now written outside `outputs/` (`VARIANTS_OUT`), so
   `scoring/scores_*.json` hold only the reference and the baselines.
8. **Docs rewritten** for the GSM8K gym: `briefing/*`, `scoring/{reference.json,
   EXPERIMENTS,TARGETS,CONSTRAINTS,DIRECTION}.md`. The paper's Table 1 and
   Table 3 GSM8K numbers are kept under `_paper_reported` (not on this scale).

All before/after numbers below come from GPU job `397cfe0e-eef` (1×H100,
1 CPU, 116 min) and `redteam/hardening/run_checks.sh`
(`redteam/hardening/results/`). "Before" means the evaluator and the 6-attempt
outputs as this session found them; "after" means the final evaluator and the
final 20-attempt outputs. "norm" is the rank delta against the reference,
computed with the final `reference.json` coefficients. Each metric's
improvement is divided by its standard deviation across the methods in the
same scores file. Before-evaluator files lack `mislabeled_spec_rate`, so that
metric is skipped there. Metrics are given as 3-step / multistep: `y` =
`verified_fresh_yield`, `w` = `mislabeled_spec_rate`, `p` = `label_precision`.

## Do better results score higher?

Yes. On the hidden test, with paired inputs (every method is scored on the
same seeds and keys):

| Method (test) | Before: y | Before norm | After: y | After: w | After: p | After norm (test / train) |
|---|---|---|---|---|---|---|
| `vera_e_xcheck` (better: independent `solve()` cross-check, paper §5.2 fuzzing) | 0.812 / 0.711 | +1.324 | 0.800 / 0.696 | 0.094 / 0.156 | 0.928 / 0.874 | **+1.370 / +1.110** |
| `vera_e` (reference, 20 attempts) | 0.621 / 0.437 | 0 | 0.631 / 0.457 | 0.132 / 0.237 | 0.889 / 0.771 | 0 / 0 |
| `vera_e_seed1` (same pipeline, other retry seed: noise) | 0.636 / 0.420 | −0.017 | 0.653 / 0.420 | 0.127 / 0.223 | 0.891 / 0.773 | −0.029 / +0.112 |
| `vera_e_6try` (old cap) | — | — | 0.609 / 0.425 | 0.127 / 0.201 | 0.888 / 0.792 | −0.080 / +0.028 |
| `vera_e_1try` (weaker: first attempt only) | 0.412 / 0.285 | −0.975 | 0.412 / 0.281 | 0.074 / 0.125 | 0.901 / 0.824 | −0.771 / −0.650 |
| `label_copy`, `expression_search` (baselines) | failed | −2.844 | failed (p 0.009 / 0.453 < 0.7) | 1.0 | 0 | −5.843 / −5.897 |

- **Seed noise** (two runs of the reference differing only in the retry
  sampling seed) is 0.03–0.11 normalized. The better variant gains +1.11 to
  +1.37 on both splits, more than ten times that.
- **The paper's claim, in the paper's direction:** the validate-and-retry loop
  raises certified families, 0.422 → 0.648 (3-step) and 0.286 → 0.469
  (multistep), going from 1 attempt to 20 (Table 1's "1 try" vs "≤20 tries").
  Attempts 7–20 add 35 specs (647 vs 612 of 848 seeds). That gain, 6 → 20
  attempts, is within noise; 1 → 20 is not.
- **Train and test agree** for the reference: y = 0.627 / 0.454 on train vs
  0.631 / 0.457 on test.

## Shortcuts: fix, and score before → after

| Shortcut (`redteam/hardening/build_shortcuts.py`) | Fix | Test norm before → after |
|---|---|---|
| **Speculative fill**: reference plus brute-force specs for every uncovered seed; yield up, multistep `w` 0.237 → 0.438 | `mislabeled_spec_rate`, coefficient 1.5 | **+0.385 → −0.240** (train −0.350) |
| **Key-blind generator**: fixed per-seed list walked by call count | reverse-order replay | **+0.018 (tie) → −2.920** |
| **Hold slots at seed values**: before, certified 0.650 vs 0.638 and p 0.907 vs 0.888 on 3-step, beating the reference on 2 of 3 metrics | every slot must vary | −0.210 → **−2.721** |
| **Hidden failed method** (`_name/` without specs, `.name/` empty) | score every directory | not scored (rank skipped it: a tie) → **failed, −5.843** |
| **Upstream VeRA release** with labeled variants of the test seeds | removed from the repo; forbidden in `CONSTRAINTS.md` | not run (would pin down the hidden programs) → no longer in the workspace |
| **Reading the hidden references from the sandbox** | `RLIMIT_NOFILE` | defense in depth; even an exposed `open` fails |
| **Abstention**: 25 cross-checked specs per split (p = 1.0) | none needed | −2.643 → −2.063 |
| **NaN labels**, **seed echo** (seed only, no fresh variant) | none needed | failed → failed (worst values) |
| **Stronger brute force**: enumerate programs as functions and emit only when every program matching the seed agrees at probe points (`consensus_bruteforce.py`) | none needed | failed → failed (p 0.656; even ungated, y 0.194 vs the reference's 0.569) |

The `REDTEAM.md` shortcuts on the AIME gym (fixed outputs, empty questions,
false evidence, moved seed, unseen H-Pro selection, ignored baseline, direct
scores) were all at +0.28 to +0.33 raw, or ties. Their counterparts no longer
exist. Seed answers and seed assignments come from `eval/`; the evaluator
generates every sample itself; nothing self-reported is read; baselines
write the same `specs.jsonl` and are scored; score files are rewritten from
scratch. The new-design versions (key-blind list, seed echo, garbage
template, empty or hidden directories, NaN) are in the table above.

## Shortcuts left open, and why

- **Public solutions of the test seeds.** GSM8K's worked solutions are
  public, including a copy under `shared/datasets/gsm8k` on this cluster, and
  so is the VeRA release. Compiling a test seed's calculator annotations
  regenerates its hidden program exactly. That is how the references were
  built, so this would score near the bound. It cannot be closed while seeds
  come from a public benchmark, which is the paper's own setting.
  `CONSTRAINTS.md` forbids it, and the grader must check for it.
- **Hand-written specs, or a stronger or remote model as the Teacher.** Test
  inputs (question, answer, slots) are visible, because the hidden test scores
  submitted specs rather than running a 7B-LLM pipeline (that would take hours
  of GPU per evaluation). `CONSTRAINTS.md` fixes the Teacher to the provided
  Qwen2.5-7B-Instruct and requires an automated pipeline. The grader checks.
- **Template faithfulness is not scored.** A template that is not a real
  question but contains every value (`sc_garbage_template`) ties the
  reference exactly (0.000) and gains nothing: the score comes entirely from
  the verifier matching the hidden program. Checking that a rendered question
  means the same as the seed needs a judge model, which a method could game;
  the paper also leaves surface realization outside verification (§5.2).
- **Validity-rule disagreements.** About 0.8% of the 6-attempt reference's
  accepted train samples (10 of 1249) carry a label that equals the raw computed value
  but are rejected by the reference program's non-negative-intermediate rule,
  because the step order differs. This is small and the same for every
  method.

## Reference score before and after

Hidden test, 3-step / multistep:

| | `verified_fresh_yield` | `certified_spec_rate` | `mislabeled_spec_rate` | `label_precision` |
|---|---|---|---|---|
| Before (old evaluator, 6 attempts) | 0.621 / 0.437 | 0.638 / 0.446 | — | 0.888 / 0.792 |
| New evaluator, 6 attempts | 0.609 / 0.425 | 0.625 / 0.433 | 0.127 / 0.201 | 0.888 / 0.792 |
| **After (new evaluator, 20 attempts)** | **0.631 / 0.457** | **0.648 / 0.469** | **0.132 / 0.237** | **0.889 / 0.771** |

The stricter evaluator costs the reference about 1.2 points of yield (slots
held fixed). The paper's 20-attempt cap gains 2–3 points back. Pooled
precision is 0.849, above the 0.7 floor.

## Headroom check

The reference sits at the bound of **no** scored metric: yield 0.63 / 0.46
(bound 1), certified 0.65 / 0.47 (bound 1), mislabeled 0.13 / 0.24 (bound 0).
An honest variant built from the paper's own suggestion (randomized
cross-checking, §5.2) beats it by more than ten times the noise and is still
far from the bounds (0.80 / 0.70 yield, 0.09 / 0.16 mislabeled). The
multistep slice is where the paper's seed-consistency gate falls short: 24%
of seeds get an accepted family that mislabels fresh variants. So it already
serves as the experiment for where the method falls short, and no extra
experiment was needed. Brute force does not pay: `expression_search` fails
(precision 0.45), and the consensus-filtered version fails (0.66) with less
than half the reference's yield. The simple baselines sit far below the
reference on a 0–1 scale with room above.

## Weights and coefficients

Both experiments keep weight 0.5. The paper does not split GSM8K by step
count, and the multistep slice already carries the most headroom.
Coefficients are `verified_fresh_yield` 1.0 (the paper's renewable verified
instances), `certified_spec_rate` 0.5 (Table 1's per-seed acceptance, here
verified against hidden programs) and `mislabeled_spec_rate` 1.5. The paper's
thesis is scale *without sacrificing* label integrity: a family with wrong
labels taints every instance it generates. At 1.0, speculative fill tied the
reference within noise on test (−0.06); at 1.5 it loses (−0.24), while the
honest variant's lead grows and the noise does not.

## Not fixed / limitations, stated plainly

- VeRA-H / VeRA-H Pro are not covered. Hardened families define new
  semantics with no external ground truth, so a hidden test could only judge
  them with a model, which a method could game. Student-model Avg@5 effects
  (the paper's 16-model tables) are not measured either. The gym measures the
  synthesis step and label integrity, not downstream benchmark difficulty.
- The Teacher is a 7B model, not the paper's frontier models. Under the
  paper's own gate, 80% / 73% of seeds get an accepted spec
  (`seed_consistency_rate`), against 100% in the paper (Table 1). The paper's
  Teacher also saw the full GSM8K solution; here, as for the paper's AIME
  seeds, it sees only the question and the answer, because with the solution a
  deterministic parser solves the task.
- Normalized ranks depend on the cohort being ranked. The margins above
  hold in this cohort of 17 methods; they are not guarantees.
- `validate.py` passes but prints a soft warning on `eval/*/sandbox_runner.py`
  ("looks detached"): the runner by design opens no files, and receives the
  method's code from `evaluate.py`, which reads it from `outputs/`.
- `REVIEW.md` did not exist; there was no earlier review to address.
- `redteam/` other than `redteam/hardening/` holds the previous audit's AIME
  cases. They target the removed gym and are kept only as evidence for
  `REDTEAM.md`.

## Reproduce

`bash scripts/run.sh` (GPU) regenerates the reference, the baselines and all
score files. The hardening checks: `VARIANTS_OUT=tmp/hardening/outputs bash
scripts/method.sh`, then `bash redteam/hardening/run_checks.sh`. The "before"
cohort needs the pre-hardening snapshot in `tmp/hardening/before/`, which is
not in git; the commit before this session (`8096990`) has that evaluator.
