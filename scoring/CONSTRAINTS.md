# Scientist Constraints

## Inputs

- A method may use, for each seed, only what `data/gsm8k_vera/*_seeds.jsonl`
  provides (question, final answer, slot schema; the worked solution exists
  only for train seeds) plus the train reference programs in
  `eval/train/references.jsonl`.
- Do not use any external source of the test seeds' solutions: the public
  GSM8K worked solutions or calculator annotations (including any copy under
  `shared/datasets/`), the VeRA paper's released datasets or generator logs
  (github.com/Marco-Cheng/VeRA artifacts), or other labeled rewrites of GSM8K.
  These contain the hidden test's ground truth.
- Do not author specifications for test seeds by hand or with any model other
  than the provided Teacher. Specifications must come from an automated
  pipeline that runs the same way on any seed.

## Teacher and compute

- The only language model is the provided Teacher,
  `data/downloads/Qwen2.5-7B-Instruct` (fetched by `scripts/download.sh`), run
  locally. No paid APIs, private endpoints, or other LLMs.
- The number of Teacher calls, prompts, sampling settings, validation and
  filtering procedures are free to change; report the Teacher budget you use.

## Evaluation protocol

- `eval/` must remain independent of `method/` and unchanged. Experiment and
  metric names in `scoring/reference.json` must be preserved.
- Submissions are `outputs/<method>/specs.jsonl` only. Every directory under
  `outputs/` is scored; a directory without a readable `specs.jsonl` is a
  failed run, so do not leave unrelated directories there.
- Labels must come from executing the submitted verifier; the evaluator
  re-runs everything itself.

## Compliance Checklist

- [ ] Specifications for test seeds use only the seed file inputs and the Teacher
- [ ] No GSM8K solutions, VeRA release artifacts, or hand-written test specs
- [ ] `eval/` untouched and not importing from `method/`
- [ ] Only `Qwen2.5-7B-Instruct` as language model, run locally
- [ ] `outputs/` contains only method directories
