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
