# Verification Report

## Initial Assessment

The workspace claimed `core_claim_plus`. That milestone is justified for the
packaged reduced gym: prior scheduler runs and the current local artifacts show
the paper's executable benchmark-specification computation running end to end
on the geometry seed family plus two additional seed families, with deterministic
replay, independent label recomputation, validation-gate checks, and paired
hard-case selection.

## Issues Found

- Minor: `briefing/evaluation.md`, `scoring/EXPERIMENTS.md`, and related
  high-level scoring docs used a few solution-oriented phrases. The artifact
  contract was correct, but the wording was less method-agnostic than it should
  be for from-scratch scientist agents.
- No critical scoring, portability, or evaluator-independence issues found.

## Fixes Applied

- Reworded method-agnostic evaluation and experiment documentation to describe
  submitted artifacts, independent checks, candidate eligibility, and benchmark
  seed families without explaining the solution implementation.
- Removed generated Python cache directories from `eval/`.
- Ran `bash scripts/evaluate.sh`, `bash scripts/evaluate_train.sh`,
  `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all
  checks passed.

## Final Judgment

The workspace is ready to serve as a research gym. Improve-mode agents can run
the existing method and compare against `scoring/scores.json`; from-scratch
agents have method-agnostic problem, evaluation, constraints, and experiment
documentation plus reusable artifact-based evaluators.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: high
- Key limitation: reduced offline reproduction of the executable generation,
  validation, replay, and hard-case selection mechanics rather than the full
  frontier-model Avg@5 evaluation suite.
