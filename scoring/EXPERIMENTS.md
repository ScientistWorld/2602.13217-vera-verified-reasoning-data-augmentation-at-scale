# Experiment Overview

## aime_geometry_vera_e_generation

Tests whether the reproduced environment can produce fresh variants of a
reasoning seed while preserving the known answer and replaying the same
generated items from fixed identifiers. This experiment establishes the core
renewable-evaluation claim in a controlled geometry setting. The evaluator
checks generated assignments and replay pairs directly rather than trusting
method-reported rates.

## aime_geometry_vera_h_hardening

Tests whether a more difficult paired item can be selected from verified
candidates while keeping labels trustworthy. This experiment checks the
boundary-evaluation setting where success requires both increased challenge and
continued label reliability. The evaluator recomputes labels from assignments
and verifies that the selected item is the highest-ranked candidate under the
fixed paired selection rule.

## aime_additional_vera_e_generation

Tests whether the same renewable-evaluation mechanics hold beyond the geometry
family. The evaluator recomputes answers for two additional paper-shown seed
families and checks that fresh generated variants remain valid and replayable.
