# Problem Definition

Static reasoning benchmarks become less useful when their items are reused,
memorized, or saturated. The problem is to turn each fixed reasoning seed into
a renewable *family* of fresh benchmark items whose labels can be trusted
without per-item human annotation or model-voting agreement.

## Task in this gym

For each seed problem (a GSM8K-style math word problem with its final answer,
and a fixed list of the numbers written in it, called slots) produce an
executable specification:

- a **template**: the question with every slot replaced by a placeholder,
- a **generator**: code that, given a random-number generator, returns new
  values for all slots,
- a **verifier**: code that, given slot values, decides whether they form a
  valid instance and returns its answer.

Sampling the generator, rendering the template and running the verifier must
yield fresh questions whose answers are correct, i.e. equal to what the seed's
own underlying calculation gives for the new numbers. The seed values must
still reproduce the seed answer.

## Research Question

How many seeds can be turned into trustworthy renewable families, and how can
one avoid families that look right at the seed but silently mislabel the fresh
items they generate?

## Why It Matters

A renewable family that emits wrong labels is worse than no family: every
instance it generates carries the error. Useful renewal therefore needs both
coverage (many seeds become families with many fresh items) and label
integrity (families with wrong labels are rare).

## Success Criteria

High coverage of seeds by families whose fresh variants are correctly labeled,
deterministically reproducible from their sampling key, and vary every number
of the question; few families that emit any wrong label.
