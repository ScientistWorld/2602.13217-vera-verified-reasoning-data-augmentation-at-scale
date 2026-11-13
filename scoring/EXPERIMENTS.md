# Experiment Overview

Both experiments ask the same question on different seeds: given a fixed
reasoning seed (a math word problem, its answer and the numbers in it), can a
method produce a renewable family of fresh questions whose labels are right,
and avoid families that look right at the seed but mislabel what they
generate? The hidden evaluator executes each submitted family on secret
sampling keys and compares every label with the seed's own underlying
calculation, so coverage (how many seeds become trustworthy families, with how
many fresh variants) and label integrity (how many families emit a wrong
label) are measured directly rather than taken from the method.

## gsm8k_vera_e_3step

Seeds whose underlying calculation has three steps. Establishes the core
renewable-evaluation claim on the easier half of the problem distribution:
fresh variants at scale with labels that stay correct.

## gsm8k_vera_e_multistep

Seeds whose calculation has four or more steps. The same claim where it is
hardest to keep labels correct off the seed; this slice separates methods that
only reproduce the seed answer from methods that capture the whole
calculation.
