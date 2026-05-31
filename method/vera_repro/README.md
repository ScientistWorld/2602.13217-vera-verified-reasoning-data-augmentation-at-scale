# VeRA Offline Reproduction

This package reproduces the executable-specification part of VeRA on three
paper-shown AIME families: the AIME-2024-II-10 geometry family, the
AIME-2024-II-9 chip-grid family, and the AIME-2024-I-11 polygon-rotation
family. It implements deterministic hash seeding, sandboxed generator/verifier
execution, VeRA-E seed consistency, VeRA-H noise-answer validation, and VeRA-H
Pro selection from verified hardened candidates.

The upstream release is cloned in `method/VeRA`. That release includes full CSV
datasets and generator artifacts, but its live Teacher/Judge/Student hooks point
to private endpoints. This package keeps the core computation offline and
reproducible.
