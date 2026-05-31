# Overview

- **Paper ID:** 2602.13217
- **Title:** VeRA: Verified Reasoning Data Augmentation at Scale
- **Domain:** Reasoning benchmark generation and evaluation
- **TL;DR:** VeRA turns static benchmark questions into executable families
  that generate fresh verified variants.

## Short Summary

The paper argues that static reasoning benchmarks invite memorization and lose
discriminative power as models improve. VeRA compiles a seed problem into a
template, generator, and verifier so new variants can be sampled and labeled
deterministically. It supports equivalent rewrites for robustness diagnostics
and hardened variants for renewed difficulty.

## Key Results

- GSM8K verified rewrites reduce the paper's conservative both-wrong artifact
  proxy from 2.12% to 0.76%.
- On AIME-2024, VeRA-E lowers the 16-model mean Avg@5 from 84.46% to 70.25%,
  exposing brittleness under verified equivalent variants.
- On AIME-2024-II, VeRA-H Pro lowers the mean Avg@5 from 84.91% to 58.57%,
  restoring headroom with verifier-certified labels.
