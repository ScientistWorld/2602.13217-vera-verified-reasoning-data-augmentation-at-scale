#!/bin/bash
# VeRA-E spec synthesis with the Teacher LLM (GPU). Writes outputs/vera_e
# (reference), outputs/vera_e_1try, outputs/vera_e_seed1 and outputs/vera_e_xcheck
# (each with specs.jsonl), refreshed after every round.
# Resumable: Teacher generations are cached in outputs/_teacher_cache/; with the
# cache present, `--replay_only` rebuilds the outputs on CPU.

set -euo pipefail
cd /home/user
python -m method.vera.synthesize --max_attempts "${MAX_ATTEMPTS:-6}"
