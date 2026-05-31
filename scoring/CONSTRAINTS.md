# Scientist Constraints

## Data

Use the provided paper-shown AIME seed families and the artifact contract
defined by this workspace: AIME-2024-II-10 geometry, AIME-2024-II-9 chip grid,
and AIME-2024-I-11 polygon rotation. Do not add external benchmark datasets
when reporting scores for the existing experiments; doing so would change the
evaluation surface rather than improve the method.

## Evaluation Protocol

`eval/` must remain independent of `method/`. A scientist may change the method
implementation, but `scripts/evaluate.sh` must score only the artifacts written
by the method. The same metric names and experiment names in
`scoring/reference.json` must be preserved.

## Label Integrity

Reported answers must come from deterministic verification or a strictly
stronger independently checkable procedure. Hardcoded score values, copied
paper numbers in `scores.json`, or labels produced by model agreement alone are
not valid.

## Resource Scope

Do not use paid APIs or private endpoints. The benchmark is intended to be
runnable offline in the compute environment after `scripts/download.sh`.

## Compliance Checklist

- [ ] Existing experiment names and metric names are unchanged
- [ ] `eval/` does not import from `method/`
- [ ] No external benchmark data is added to the reported experiments
- [ ] Labels are deterministic and not copied from paper score tables
- [ ] No paid or private API endpoints are required
