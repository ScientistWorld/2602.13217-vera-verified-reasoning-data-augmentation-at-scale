# Overview

- **Paper ID:** 2602.13217
- **Title:** VeRA: Verified Reasoning Data Augmentation at Scale
- **Domain:** Reasoning benchmark generation and evaluation
- **TL;DR:** VeRA turns static benchmark questions into executable families
  (template, generator, verifier) that generate fresh verified variants.

## Short Summary

Static reasoning benchmarks invite memorization and lose discriminative power.
VeRA compiles a seed problem into an executable specification so new variants
can be sampled and labeled deterministically, with specifications validated
(seed consistency for equivalent families) before their labels are trusted.
This gym measures the VeRA-E synthesis step on GSM8K seeds: a hidden evaluator
runs each submitted specification on secret keys and checks every label
against the seed's latent calculation.

## Key Results (paper)

- GSM8K: 1319/1319 seeds compile into accepted VeRA-E specifications on the
  first try with a frontier Teacher (Table 1); verified rewrites reduce the
  both-models-wrong artifact proxy from 2.12% to 0.76%.
- AIME-2024: VeRA-E lowers the 16-model mean Avg@5 from 84.46% to 70.25%.
- AIME-2024-II: VeRA-H Pro lowers the mean Avg@5 from 84.91% to 58.57%.

## This gym

Reference: the paper's synthesis loop with a local Qwen2.5-7B-Instruct
Teacher. Scores are in `scoring/scores_test.json` (hidden test) and
`scoring/scores_train.json`; see `briefing/evaluation.md` for the protocol.
