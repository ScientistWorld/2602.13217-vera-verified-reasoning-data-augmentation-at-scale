# Verification Report

Final state after the iteration-11 hardening (see `HARDENING.md`).

- Milestone: core_claim_plus. The paper's VeRA-E synthesis loop (Teacher
  proposal, schema / compile / runtime / yield / seed-consistency gates,
  feedback retries up to 20, hash-seeded sampling, sandboxed execution) runs
  end to end on GSM8K seeds. Its Table 1 effect (retries raise accepted specs)
  appears in the paper's direction, and label integrity is measured against
  hidden latent programs on two difficulty slices.
- `python validate.py` passes (one soft heuristic warning on the sandbox
  runner, explained in `HARDENING.md`).
- Job `397cfe0e-eef` produced the reference outputs and score files from the
  final code; the hardening checks ran through the hidden-test evaluator.
- Key limitation: a 7B local Teacher (not frontier models); VeRA-H and
  Student-model accuracy tables are out of scope.
