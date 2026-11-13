# Evaluation

## Data

- `data/gsm8k_vera/train_seeds.jsonl` (221 seeds) and
  `data/gsm8k_vera/test_seeds.jsonl` (627 seeds): `seed_id`, `question`,
  `answer` (a non-negative integer), and `slots` — one per number written with
  digits in the question: `name` (`n0`, `n1`, ...), `text`, `value`, `kind`
  (`int` or `float`), and character offsets `start` / `end`.
- Train seeds also carry the worked GSM8K `solution`, and
  `eval/train/references.jsonl` holds the train reference programs (the
  seed's calculation as a list of arithmetic steps over the slots). Test seeds
  carry neither; their references are hidden.
- Seeds are GSM8K problems with at least three calculation steps whose
  reference program could be recovered unambiguously from the official
  calculator annotations.

## Submission

Each method writes `outputs/<method>/specs.jsonl`, one JSON object per seed:

```json
{"seed_id": "te0001", "template": "... {n0} ... {n1} ...",
 "generator_code": "def generator(rng): ...  # returns {'n0': ..., 'n1': ...}",
 "verifier_code": "def verifier(assign): ...  # returns (True, answer) or (False, None)"}
```

Every directory under `outputs/` is scored as a method, whatever its name; a
directory without a readable `specs.jsonl`, or with a duplicated `seed_id`,
is a failed run. A seed without a row scores zero. Nothing else a method writes
is read.

Code rules (checked statically and enforced at run time in a subprocess):
Python only; imports limited to `math`, `random`, `fractions`, `itertools`,
`functools`; no names or attributes starting with an underscore (`__` in names
or strings), no `eval/exec/open/getattr/type/...`, no classes, at most 20000
characters per field. `rng` offers `random, uniform, randint, randrange,
choice, choices, sample, shuffle, gauss, triangular`. Each call has a 2-second
timer; the process has 60 CPU-seconds, 1 GB of memory, and no file access.
Template placeholders must be exactly the seed's slot names in plain `{name}`
form (no format specs), the template at most 4000 characters.

## Protocol per seed

The evaluator executes the submitted code itself; it never reads a label or
flag the method wrote.

1. The verifier is called on the seed's slot values.
2. The generator is called with 8 secret keys (`random` is also seeded with the
   key). Each sample is replayed in an independent namespace with the keys
   walked in reverse order; a sample must depend only on its key.
3. A sample is **fresh** if its slot values differ from the seed values (int
   slots must be integers, all values positive and at most 1e9).
4. For each fresh sample the verifier accepts, the label is compared with the
   hidden reference program evaluated on the same values. The reference
   accepts an assignment only if no step divides by zero, every intermediate
   quantity is non-negative, and the final answer is a non-negative integer;
   a verifier that accepts an assignment the reference rejects, or returns a
   different value, has given a **wrong label**.
5. A fresh sample is **counted** if its label is correct, it replays exactly,
   and the template renders it into a question containing every slot value
   (at least a quarter of the seed question's length).
6. The seed is **certified** if the verifier returns the seed answer at the
   seed values, no accepted fresh sample has a wrong label, at least one
   sample is counted, and every slot takes a non-seed value in some counted
   sample. It is **mislabeled** if any accepted fresh sample has a wrong label.

## Metrics (per experiment, averaged over all its seeds)

| Metric | Direction | Meaning |
|---|---|---|
| `verified_fresh_yield` (primary) | higher | mean over seeds of (distinct counted samples / 8) for certified seeds, 0 otherwise |
| `certified_spec_rate` | higher | fraction of seeds certified |
| `mislabeled_spec_rate` | lower | fraction of seeds mislabeled |
| `label_precision` | higher (unweighted) | correct / accepted fresh samples, pooled |
| `seed_consistency_rate` | higher (unweighted) | fraction of seeds whose verifier returns the seed answer and accepts a fresh sample |

**Failure.** If the pooled `label_precision` over all seeds is below 0.7, or
the submission is unreadable, the method fails: every metric of every
experiment gets its worst value (0, and 1.0 for `mislabeled_spec_rate`).

## Experiments

- `gsm8k_vera_e_3step` — seeds whose reference program has 3 steps
  (403 test / 142 train seeds), weight 0.5.
- `gsm8k_vera_e_multistep` — seeds with 4 or more steps (224 test / 79 train
  seeds), weight 0.5.

## Running

- `bash scripts/evaluate_train.sh` scores every directory under `outputs/` on
  the train seeds with public keys and writes `scoring/scores_train.json`
  (`scripts/evaluate.sh` writes the same numbers to `scoring/scores.json`).
- `bash scripts/evaluate_test.sh` (no arguments) scores every directory under
  `outputs/` on the hidden test seeds with secret keys and writes
  `scoring/scores_test.json`.

## Baselines

- `label_copy`: perturbs the numbers but keeps the seed answer as every
  label (unverified surface perturbation). Fails the precision floor.
- `expression_search`: brute-force search for an arithmetic expression over
  the slots that reproduces the seed answer. Coincidental matches mislabel
  fresh variants; fails the precision floor.
