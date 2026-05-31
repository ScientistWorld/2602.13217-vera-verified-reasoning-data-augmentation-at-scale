# VeRA Offline Reproduction

This package reproduces the executable-specification part of VeRA on the
AIME-2024-II-10 geometry family shown in the paper. It implements deterministic
hash seeding, sandboxed generator/verifier execution, VeRA-E seed consistency,
VeRA-H noise-answer validation, and VeRA-H Pro selection from verified hardened
candidates.

The upstream release is cloned in `method/VeRA`. That release includes full CSV
datasets and generator artifacts, but its live Teacher/Judge/Student hooks point
to private endpoints. This package keeps the core computation offline and
reproducible.

