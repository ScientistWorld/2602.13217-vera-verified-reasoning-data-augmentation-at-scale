# Research Direction

## Research Problem

Renewable reasoning evaluation: turning fixed reasoning seeds into executable
families that generate fresh, reliably labeled variants, so evaluation can
scale without relabeling and without trusting labels that were never checked.

## Core Contribution

Work must stay centered on executable benchmark specifications (template,
generator, verifier) synthesized automatically from a seed and validated
before their labels are trusted. Improvements should raise how many seeds
become trustworthy families and lower how many accepted families mislabel
fresh variants.

## Approach Scope

In scope: specification synthesis prompts and feedback, retry and sampling
strategies for the provided Teacher, stronger spec-level validation (e.g.
independent re-derivation, randomized fuzzing, consistency checks across
candidate specifications), generator design (coverage of every slot, sensible
ranges, exact divisions), abstaining on seeds that cannot be validated, and
combining the Teacher with program search.

## Out of Bounds

- Using worked solutions or other external labels for the test seeds
- Replacing the Teacher with a stronger or remote model, or hand-writing
  specifications for test seeds
- Replacing deterministic verification with model-only answer voting
- Changing the evaluator, the seeds, or metric directions
