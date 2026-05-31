# Research Direction

## Research Problem

The research problem is renewable reasoning evaluation: turning fixed reasoning
seeds into fresh, reliably labeled variants that remain useful when static
benchmarks become familiar or saturated.

## Core Contribution

Work must stay centered on executable benchmark specifications: a structured
way to render variants, generate valid parameters, and compute labels through
deterministic verification. Improvements should strengthen validity,
generality, reproducibility, or difficulty calibration within that framework.

## Approach Scope

Scientists may improve specification synthesis, generator quality, verifier
coverage, validation filters, replay controls, candidate selection, or
artifact/evaluation interfaces. They may add more seed families if they also
extend the reference and score structure consistently.

## Out of Bounds

- Replacing deterministic verification with model-only answer voting
- Reporting static benchmark accuracy without generating fresh variants
- Changing the problem into general LLM benchmark evaluation without executable
  specifications
- Beating scores by adding unrelated easier seeds or changing metric direction
