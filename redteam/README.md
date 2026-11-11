# Scoring audit

Run `bash redteam/run_all.sh` in a CPU job. Each case also has its own `run.sh`.
No case imports the hidden evaluator to construct a method or its labels.
Static shortcuts use the answer computation already exposed in `eval/train/`.
Every case invokes the unmodified `bash scripts/evaluate_test.sh` with no
arguments, in a fresh subprocess with no artifact-selection environment overrides.
All artifacts needed by that subprocess are ordinary files surviving process exit.

`run.json` records commands, exits, failures and whether a failed test left stale
scores. `scores_test.json` is the exact file found after that case's hidden run;
when the test failed it is explicitly marked stale and is never counted as a
successful score. Generated artifact directories and full logs are ignored;
the retained summaries and scores provide compact evidence. Re-running a case
reconstructs its artifacts.

The original packaged method imports a missing, untracked `core.py` and fails.
`recovered_core.py` supplies the documented executable-specification computation
for conditional checks only. It does not repair the gym. Its explicit SHA256
encoding may differ from the missing original; seed reruns are therefore labeled
recovered, never reported as exact reruns of the original reference.

Quality controls: `better_generator` expands numerical supports while retaining
the existing specification driver, validators, verifier snippets and H-Pro rule.
`more_samples64` changes only sample count. `weaker_random_labels` applies the
provided random-answer baseline to generated labels while retaining other
artifacts, to isolate the penalty for incorrect answers. `shortcut_ignored_baseline`
runs the supplied baseline without adaptation and checks method discovery.

The audit saves and restores pre-existing outputs and both split-score files for
every case. It never modifies `eval/`, the test script, the Python environment,
baselines, datasets or the packaged method. The audit's original reference values
are frozen in `reference_scores_test.json`; metric definitions and coefficients
are frozen in `reference_config.json`. These snapshots are for reporting only.

`summary.json` reports raw weighted metric deltas AND standardized deltas using
population standard deviations over successful audit runs. The latter implement
the stated ranking rule for this explicit cohort; they cannot predict exact ranks
under an unknown distribution of future attempts. A strict metric-wise dominance
claim remains true under any positive per-metric scaling.

The shortcut now named `shortcut_ignored_baseline` was measured under the name
`baseline_ignored` in the bundled job. Its directory and runnable case were renamed
only to make the shortcut terminology explicit; its original `run.json` and score
files are retained unchanged.
