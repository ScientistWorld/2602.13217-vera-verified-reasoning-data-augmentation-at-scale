# Audit: does this gym reward better research?

**The scoring does not establish a reliable ordering of scientific quality.** A broader, genuinely more varied generator improved the hidden score by less than the observed seed spread. Increasing generation from 8 to 64 samples per specification expanded coverage but scored substantially worse. A clearly weaker random-label control scored lower, as expected. More seriously, four fixed outputs, empty questions, and fabricated validation evidence all beat the cached reference. Changing the submitted seed ground truth achieved every scored metric's upper bound.

**The paper's reported baseline effect is not measured here.** The supplied random-answer baseline is omitted by the hidden evaluator, and no Student-model seed-versus-variant accuracy or hardness comparison is scored. Thus this audit cannot confirm that the reproduced method beats its baseline in the direction reported by the paper. The packaged method also fails to run because `method/vera_repro/core.py` is missing. These are limitations of the starting gym, not audit changes.

The CPU job `9167f99d-d52` completed all 20 cases: 18 successful hidden evaluations and two expected failures. Each case has a runnable `redteam/<case>/run.sh`, its exact `scores_test.json`, and command/exit evidence in `run.json`. The two failed evaluations retain explicitly marked **stale** score snapshots, which are excluded from all score comparisons. See [machine-readable results](redteam/summary.json), [compact results](redteam/summary.tsv), [audit runner](redteam/audit.py), and [final record checks](redteam/verification.json).

## Better and weaker methods

All deltas below are relative to the audit-start `vera_repro` test results, confirmed unchanged by [cached_reference](redteam/cached_reference/run.json). Its delta is zero. The rightmost column compares with the matched recovered seed 0 rather than the cached reference.

| Variant and actual method change | Raw weighted delta | Audit-normalized delta | Normalized delta vs matched seed 0 |
|---|---:|---:|---:|
| [Cached reference](redteam/cached_reference/run.sh) | 0 | 0 | — |
| [Recovered seed 0](redteam/reference_seed0/run.sh) | +0.02425 | +0.01573 | 0 |
| [Better generator](redteam/better_generator/run.sh): expand geometry, grid, and polygon numerical supports; keep driver, templates, verifiers, validation gates, replay and H-Pro procedure | +0.04300 | +0.06881 | +0.05309 |
| [More data](redteam/more_samples64/run.sh): 64 rather than 8 samples per specification, same seed and pipeline | −0.22675 | −0.62931 | −0.64504 |
| [Weaker random labels](redteam/weaker_random_labels/run.sh): replace generated labels with the supplied baseline's seeded random-integer predictions | −2.09000 | −5.75794 | −5.77366 |

The better generator's distinct numerical assignments among eight outputs per family increased from 6 to 8 for geometry, 5 to 8 for chips, and 4 to 5 for polygons, while retaining independently recomputed label validity. Its matched gain, +0.05309, is below the recovered three-seed range of **0.09693**. Even its +0.06881 gain over the cached reference is below that range. A reliable improvement larger than noise was **not** demonstrated.

The 64-sample run increased numerical coverage from 6/5/4/3 to 7/5/5/5 across geometry/chips/polygons/H, retaining validity, validation and replay rates of 1. Its score nevertheless fell far beyond the seed spread. The uniqueness metrics divide distinct assignments or hardness ranks by the submitted row count; generating more of a small finite support lowers those rates. For example, additional-family assignment diversity fell from 1 to 0.15625, and H hardness diversity fell from 0.5 to 0.15625, although H mean rank rose from 0.4 to 0.5375. This is expanded coverage with more duplicates, not a claim of improvement on every distributional property. The scoring incentivizes small handpicked submissions and does not measure useful renewable scale.

The random-label control had zero correct generated labels on the test. It loses decisively, but detached seed, replay, gate and candidate-pool fields still earn credit. That sanity check does not rescue the successful task-failing shortcuts below.

## Seed spread and reproduction check

The original [method run](redteam/original_method/run.json) exits 1 with `ModuleNotFoundError: No module named 'method.vera_repro.core'`. That module is imported by both the driver and specification definitions but is absent from the tracked package. The global `core.*` ignore rule could explain its omission; this is an inference. Exact three-seed reruns of the original reference are therefore unavailable.

For a conditional estimate, [recovered_core.py](redteam/recovered_core.py) implements the documented executable-specification support under `redteam/`, and [recovered_runner.py](redteam/recovered_runner.py) runs the unchanged packaged driver and snippets against it. It uses explicit SHA256 hash seeding and subprocess execution. The original hash serialization and sandbox implementation are unknown, so **these are recovered-method runs, not exact original-reference reruns**. No recovery was installed into `method/` or the evaluator's Python environment.

| Recovered seed | Raw delta vs cached reference | Audit-normalized delta |
|---|---:|---:|
| [0](redteam/reference_seed0/scores_test.json) | +0.02425 | +0.01573 |
| [1](redteam/reference_seed1/scores_test.json) | +0.00925 | +0.01212 |
| [2](redteam/reference_seed2/scores_test.json) | −0.03100 | −0.08120 |
| Max minus min | **0.05525** | **0.09693** |
| Population standard deviation | 0.02333 | 0.04487 |

Per-metric seed values and ranges are in `summary.json`. Notable ranges are 0.5 for H novelty, 0.3 for H mean rank, 0.375 for additional-family novelty, and 0.5 for additional-family assignment diversity. Gains below this observed spread should be treated as noise. Three recovered seeds cannot establish the missing original method's true spread.

The cached artifacts reproduce the three example seed answers, 468, 902 and 371, with validity and replay fields at 1. That confirms the small examples' arithmetic, not the paper's scientific effect. The supplied [baseline](baseline/random_answer.py) writes `outputs/baseline/random_predictions.jsonl`, which does not satisfy the evaluator's seven-file contract. Running it produces no baseline entry in test results. The adapted random-label control above shows that an incorrect-answer baseline can score lower once represented in the contract; there is no native controlled baseline comparison.

Compared with the [paper](paper/2602.13217.md), especially Sections 3.1–3.5 and 4, the reproduction departs in these material ways:

- Four manually authored executable specifications replace Teacher-model proposal, validation-feedback and repair. There is no automatic synthesis over new seeds.
- An offline numerical equality check replaces the independent Judge's assessment of rendered questions. The driver constructs two correct and three perturbed trials but does not randomize their order; the hidden evaluator uses one correct and three perturbed numerical comparisons. Neither tests whether the question and verifier semantics agree.
- H hardening uses one fixed geometry transformation and five fixed parameter tuples. H-Pro selects among eight sampled instances by a hardcoded tuple rank, rather than the paper's default five verified hardened candidates, possibly from different specifications, with difficulty ranking. The rank is not calibrated against Student performance.
- Eight outputs per family and three AIME seed families replace the broad benchmark and 16-model experiments. No paired Avg@5, seed familiarity diagnostic, Student hardness effect, synthesis acceptance/cost, or amortized scaling effect is evaluated. The bundled upstream CSVs are not consumed by this hidden test.
- Deterministic hash seeding and sandbox execution are claimed by the package, but the implementing core is missing; their historical behavior cannot be verified from the shipped implementation.

This is a scaled-down, hand-authored substitute for the paper's experiment. It preserves some generation arithmetic, but does **not** demonstrate the studied robustness or calibrated-hardening effects. A better score here is not evidence of a better method on the paper's problem.

## Shortcut runs

The table gives one row per attempted shortcut. Reference delta is 0 in both score columns. Every linked directory contains `run.sh`, `run.json`, and the actual test score file. Successful shortcuts use only visible train-evaluator formulas and, where available, method generators; they do not use paper answers or hidden-only labels to construct outputs. Static tables duplicate each item into both index parities, so they require no hidden split knowledge.

| Shortcut | What it does | Raw delta vs reference | Audit-normalized delta vs reference | Outcome |
|---|---|---:|---:|---|
| [shortcut_enumeration](redteam/shortcut_enumeration/run.sh) | Exhaust every finite generator case: 21 geometry assignments including wording styles, 5 chip cases, 5 polygons and 5 H tuples; compute answers from visible formulas and submit a static table. | +0.14200 | +0.36077 | **Works** in this audit cohort; no renewable method. |
| [shortcut_constant](redteam/shortcut_constant/run.sh) | Submit only four fixed outputs, one per family, with copied replay pairs and asserted gates. | +0.28100 | +0.77497 | **Works**; componentwise dominates reference. |
| [shortcut_empty_questions](redteam/shortcut_empty_questions/run.sh) | Same fixed outputs with every question empty, the rendered `answer` set to 0, and impossible negative elapsed times. Keep only `numeric_answer` correct. | +0.28100 | +0.77497 | **Works**; cannot deliver reasoning questions yet outranks reference. |
| [shortcut_false_evidence](redteam/shortcut_false_evidence/run.sh) | Set acceptance flags to the truthy string `"false"`, declare mode-specific gates false and validation count zero; use unrelated identical replay assignments `{}` and answers 123. | +0.28100 | +0.77497 | **Works**; gate and replay rates remain 1. |
| [shortcut_moved_seed](redteam/shortcut_moved_seed/run.sh) | Replace canonical base assignments and expected answers; select the original rank-5 H tuple while changing its submitted novelty anchor. | +0.33000 | +0.93932 | **Works**; **all 22 weighted metrics equal 1**, the global maximum. |
| [shortcut_unseen_hpro](redteam/shortcut_unseen_hpro/run.sh) | Replace the selected artifact by a valid fractional assignment and new ID absent from variants and candidate pool. Integer truncation gives it the same maximum rank as the pool. | +0.28100 | +0.77497 | **Works**; both selection-integrity metrics remain 1. |
| [shortcut_omitted_method](redteam/shortcut_omitted_method/run.sh) | Leave a complete failed method directory on disk, but remove its name from editable `scores_train.json` before the default hidden run; retain a decoy method. | **0 for the omitted method** | **0 for the omitted method** | **Works, shortcut tie under the specified skip-missing rule**. Decoy separately earns +0.28100 / +0.77497. |
| [shortcut_ignored_baseline](redteam/shortcut_ignored_baseline/run.sh) | Run the real random-answer baseline beside cached reference artifacts. Its incomplete contract is ignored. | 0 | 0 | **Shortcut tie**: hidden results contain reference only; absent baseline avoids losses under skip-missing. |
| [shortcut_direct_scores](redteam/shortcut_direct_scores/run.sh) | Prewrite an astronomical test `valid_rate` and null seed metric, retaining cached reference artifacts. | 0 | 0 | **Shortcut tie from cached artifacts; score injection fails** because the successful hidden run overwrites both fake values. |
| [shortcut_nonfinite](redteam/shortcut_nonfinite/run.sh) | Submit NaN/Infinity as generated numerical answers. | −2.09000 | −5.75794 | **Fails**; generated-answer validity becomes zero. |

`shortcut_ignored_baseline` was named `baseline_ignored` in the original job log and raw `run.json`; only its directory and runnable case name were subsequently renamed to make the shortcut terminology explicit. Measurements are unchanged.

The four-output shortcut's answers are 72, 2, 47 and approximately 1942.84444. With one scored row per family it obtains perfect uniqueness and novelty; H mean rank is 0.8 and every other weighted metric is 1. There is no submitted executable generator, verifier or proof of replay. The empty-question shortcut has exactly the same metric vector. This supplies a direct counterexample to the requirement that a task-failing method cannot outrank the reference through other metrics: even the purported validity/constraint metrics do not check delivery of a valid question family.

The moved-seed shortcut changes the E geometry base to `(101,3)`, the chip base to a 6×6 full-capacity grid, the polygon base to `n=3`, and the H base to `(11,3,45)`. It computes their internally consistent answers, then emits rank-5 H outputs. The evaluator treats these method-controlled answers as gold. No stronger reasoning, synthesis or independent validation is involved.

The unseen-H-Pro shortcut selects `(31.25,8.25,70.25)` while its pool contains `(31,8,70)`. Its [run record](redteam/shortcut_unseen_hpro/run.json) confirms `selected_assignment_present_in_pool: false`. The evaluator independently recomputes the selected answer, but compares **rank equality**, not actual membership, so a replaced fixed selection artifact passes.

Brute-force enumeration uses **36 table entries covering all 22 distinct numerical cases in the packaged generators**, including all three geometry wordings. Chip and polygon color attributes are omitted because they do not change the computation. The visible evaluator already supplies the label formulas, including direct combinatorial enumeration for grids and polygons. The resulting static table beats the reference. The reference's supports are too small, and the hidden test imposes no fresh challenge outside this table. Although broader assignments are accepted, there is no incentive to handle unseen inputs. This enumeration win is cohort-dependent because its mean H rank is lower; the fixed-output, empty-question, false-evidence, moved-seed and replaced-selection shortcuts instead weakly improve every weighted metric and strictly improve some, so their wins survive any positive per-metric scaling.

There is no trained model treated as fixed by this evaluator, so retraining a fixed reference model is inapplicable. Replacing the supposedly fixed selection artifact and moving canonical seed answers were tested instead. No evaluator-process or Python-environment manipulation was used.

## Bounds, rank arithmetic and failure handling

All 22 nonzero-coefficient metrics are rates bounded by [0,1], all use `higher_is_better: true`, and all coefficients are positive. The three `verified_variant_count` diagnostics have coefficient zero. Experiment weights are 0.35 for geometry E, 0.30 for additional E, and 0.35 for H. Absolute coefficient magnitude, not its sign, is used throughout this report.

**15 of 22 weighted metrics already sit at their upper bound of 1:**

| Experiment | Every reference metric already at its bound |
|---|---|
| `aime_geometry_vera_e_generation` | `seed_consistency_rate`, `valid_rate`, `valid_assignment_diversity_rate`, `validation_gate_pass_rate`, `deterministic_replay_rate` |
| `aime_additional_vera_e_generation` | `seed_consistency_rate`, `valid_rate`, `valid_spec_coverage_rate`, `validation_gate_pass_rate`, `deterministic_replay_rate` |
| `aime_geometry_vera_h_hardening` | `noise_judge_pass_rate`, `validation_gate_pass_rate`, `h_candidate_pool_valid_rate`, `h_pro_selected_from_valid_pool`, `h_pro_selected_ranked` |

The remaining reference values are geometry-E novelty 0.75; additional-E assignment diversity 0.75 and novelty 0.75; H assignment diversity 0.75, hardness diversity 0.75, novelty 0.5 and mean rank 0.75. The raw weighted utility is 4.25 out of a possible 4.58. Thus the reference can be beaten, but most constraint metrics are saturated and the remaining headroom is readily claimed by shortcuts. The unadapted baseline is not scored at all; the adapted random-label baseline is clearly below reference. Stale target values in `reference.json` also differ from actual test results and omit some newly scored metrics, so this report uses the audit-start test results as the reference vector.

For explicit calculations, raw delta is `sum(weight * abs(coefficient) * direction * (value - reference))`; it is a units-dependent diagnostic, **not** the specified normalized rank. Audit-normalized delta additionally divides each metric's improvement by its population standard deviation across the 18 successful cases named in `summary.json`. This implements the supplied rule for this explicit audit cohort, including duplicate outcomes and the empty-artifact control. Unknown future attempts will change those standard deviations, so these numbers do not predict their exact ranks. All weighted metric standard deviations in this cohort are positive. Missing values contribute no delta, as specified. Componentwise dominance arguments above do not depend on this cohort choice.

| Required check and concrete run | Observed hidden-test behavior | Verdict |
|---|---|---|
| [failed_empty](redteam/failed_empty/run.sh): all seven contract files present, empty rows and empty summary | Exit 0; every weighted metric in every experiment is explicitly 0. Raw delta −4.25, normalized delta −15.18772. | Passes for this representation of failure. |
| [failed_incomplete](redteam/failed_incomplete/run.sh): only an empty variants file | Exit 1; old score file remains byte-for-byte unchanged, with no worst-value record. | Fails total failure handling. Stale scores are **not** counted as a successful shortcut. |
| Original method failure | Missing core prevents generation; hidden test also exits 1 and leaves stale scores. | A real failed run likewise gets no explicit worst-value vector. |
| Every method on disk must be written under experiment `results` | `shortcut_omitted_method` leaves a complete empty method on disk. Train scores initially contain it; editing the train registration removes it from every hidden experiment. | Fails discovery completeness. Skip-missing gives that omitted method a tie instead of the empty method's −15.18772. |
| Nonfinite numeric answers and prewritten scores | Nonfinite labels lose validity; successful hidden evaluation overwrites fake score/null fields. | Those particular injections fail. Other artifact assertions are trusted, as demonstrated above. |

The test script passes `scoring/scores_train.json` as its method list. A nonempty list restricts discovered output directories instead of ensuring that every directory is scored. Incomplete directories are ignored unless requested, in which case discovery raises. Scores are written only after all evaluations finish. Consequently the successful zero-vector case does not imply general failure completeness.

## Evidence and scope

The artifact evaluator never executes submitted generators or verifiers. Numeric validity comes from `numeric_answer` and `assignment`; it ignores rendered `question` and `answer`. Replay compares two submitted copies without regenerating from IDs or connecting the copies to the scored variants. Gate metrics use boolean coercion of assertions and ignore the mode-specific false fields. Base checks compare against submitted assignments and expected answers. H-Pro membership is rank equality. These behaviors are in [the evaluator](eval/test/evaluate.py); the visible train evaluator exposes the same formulas and ranking, differing only in split parity and default output path.

Every case first finishes its artifact-building command, runs the visible train script, and then invokes **`bash scripts/evaluate_test.sh` with no arguments** as a separate process. Artifact-selection environment overrides are removed. The unmodified gym `eval/` and test script were used throughout the CPU container job. No case depends on a process surviving construction, a modified evaluator, evaluator environment, or hidden-only answers. Only ordinary persisted outputs and, for discovery, the editable train registration affect the hidden run. The hidden score snapshots are used for reporting, never to construct labels.

All temporary outputs and score files were restored after each case. The temporary job entrypoint was restored from audit-start git. The final audit changes are `redteam/` and this report, plus the required `action.yaml` completion signal. Pre-existing system-managed README/manifest and trajectory status is recorded in [start_status.txt](redteam/start_status.txt) and left untouched. No gym scoring fixes were made in this iteration.
