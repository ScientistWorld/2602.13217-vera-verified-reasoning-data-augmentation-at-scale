# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Work is continuing toward `core_claim_plus`; no stop requested.
