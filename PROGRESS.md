# Progress

## Current gym (iteration 11, hardened)

- Task: VeRA-E executable-specification synthesis on GSM8K seeds (>= 3
  calculation steps); 627 hidden test / 221 train seeds; experiments
  `gsm8k_vera_e_3step` and `gsm8k_vera_e_multistep`.
- Hidden evaluator (`eval/test/`) executes submitted template / generator /
  verifier code in a sandbox on secret keys and checks every label against
  the seed's latent program recovered from GSM8K calculator annotations.
- Reference (`method/vera/`): the paper's synthesis loop (schema, compile,
  runtime, yield and seed-consistency gates, feedback retries, up to 20
  attempts) with a local Qwen2.5-7B-Instruct Teacher.
- Baselines: `label_copy`, `expression_search` (both fail the 0.7 precision
  floor).

## Results (hidden test, 3-step / multistep)

- Reference `vera_e`: verified_fresh_yield 0.631 / 0.457, certified 0.648 /
  0.469, mislabeled 0.132 / 0.237, precision 0.889 / 0.771.
- First-attempt-only variant: yield 0.412 / 0.281 (retries help, as in the
  paper's Table 1). The cross-checked variant: yield 0.800 / 0.696 (headroom).
- Seed noise (other retry seed) is about 0.03–0.11 normalized rank;
  better variant +1.37.

## Deviations from the paper

- 7B local Teacher instead of frontier models; the Teacher sees question and
  answer only (not the GSM8K worked solution).
- Fixed slot schema (one slot per digit-written number) and one template per
  spec, so the hidden test can check labels.
- VeRA-H / H-Pro and Student-model Avg@5 tables are not reproduced.

See `HARDENING.md` for the shortcut audit and the before/after numbers.
