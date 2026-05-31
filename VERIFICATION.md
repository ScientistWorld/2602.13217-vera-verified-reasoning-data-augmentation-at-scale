# Verification Report

## Initial Assessment

The workspace claimed `core_claim_plus`. That claim was broadly justified: the
packaged method runs offline, generates verified reasoning variants from three
paper-shown families, recomputes labels in `eval/`, and has prior successful
scheduler-job evidence. The reproduction is intentionally reduced in scope: it
does not reproduce the paper's large-scale frontier-model Avg@5 evaluation, but
it does reproduce the core renewable-generation and label-integrity mechanics
needed for a usable gym.

## Issues Found

- Minor: `briefing/evaluation.md` and `scoring/EXPERIMENTS.md` used some
  paper-specific solution vocabulary in files intended to be method-agnostic.
- Minor: `eval/train/` and `eval/test/` did not yet require or score the new
  validation-gate and hard-candidate-pool artifacts, so hidden scoring checked
  fewer integrity constraints than the main evaluator.
- Minor: `scoring/reference.json` used reduced gym targets rather than direct
  paper table values without explicitly documenting that scaling choice.

## Fixes Applied

- Reworded strict method-agnostic documentation to describe the task and
  artifact contract without solution-specific labels.
- Extended `eval/train/evaluate.py` and `eval/test/evaluate.py` to require
  `spec_validation.jsonl` and `h_candidate_pool.jsonl`, and to score
  `validation_gate_pass_rate`, `h_candidate_pool_valid_rate`, and
  `h_pro_selected_from_valid_pool`.
- Added notes in `scoring/reference.json` explaining that the reference values
  are reduced offline gym targets for generation, validation, replay, and
  selection mechanics rather than the paper's full model-evaluation tables.
- Re-ran `bash scripts/reproduce.sh`, `bash scripts/evaluate_train.sh`,
  `bash scripts/evaluate_test.sh`, and `python validate.py --compare`; all
  checks passed.

## Final Judgment

The workspace is ready to serve as a reduced research gym. Improve-mode agents
can modify the method and be scored through the same artifact interface.
From-scratch agents have a method-agnostic problem statement, evaluation
contract, and scoring docs. The main limitation is scope: the gym focuses on
offline verified generation and hard-case selection mechanics, not full
large-scale model accuracy evaluation across all paper datasets.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: high
- Key limitation: reduced offline reproduction of verified generation mechanics,
  not the paper's full frontier-model benchmark suite

## Reactivation Audit

On 2026-05-31 06:28 UTC, a follow-up audit re-read the paper's method and
experiment sections with a subagent, checked the current implementation against
the extracted workflow, and reran the packaged scripts locally:

- `bash scripts/reproduce.sh`
- `python validate.py --compare`

Both passed. No new implementation defects were found, and the existing
`core_claim_plus` milestone remains the honest stopping point for this reduced
offline reproduction.
