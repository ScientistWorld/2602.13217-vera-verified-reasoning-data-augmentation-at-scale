# Paper's Method

## Key Contribution

VeRA represents benchmark items as executable specifications that can generate
fresh verified variants on demand. This separates benchmark scale from the cost
of relabeling every item.

## Approach

Each specification contains a natural-language template, a deterministic
generator for valid slot assignments, and a deterministic verifier that checks
the assignment and computes the canonical answer. Sampling uses a hash of
immutable identifiers, so variants are reproducible.
Generator and verifier snippets are executed in a restricted sandbox with
deterministic builtins and math-only imports.

VeRA-E keeps the seed semantics fixed and accepts a specification only when the
verifier reproduces the seed answer. VeRA-H changes the task to make it harder
while keeping labels verifier-certified. VeRA-H Pro selects the hardest verified
candidate from a fixed hardened candidate pool.

This reproduction clones the upstream release in `method/VeRA` and adds a small
offline implementation in `method/vera_repro`. The released live Teacher, Judge,
and Student hooks require private endpoints, so the runnable experiment uses
paper-shown AIME executable families directly: the AIME-2024-II-10 geometry
family, the AIME-2024-II-9 chip-grid family, and the AIME-2024-I-11
polygon-rotation family. The reproduction preserves the core
executable-specification computation.

## Main Claims

The primary claim reproduced here is that executable specifications can produce
fresh, verifier-labeled variants at near-zero marginal cost while preserving
label integrity. A secondary reproduced claim is that hardened variants can be
selected from verified candidates under a paired VeRA-H Pro protocol.
