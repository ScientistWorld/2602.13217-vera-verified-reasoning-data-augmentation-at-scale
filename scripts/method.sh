#!/bin/bash
# VeRA-E spec synthesis with the Teacher LLM (GPU): up to 20 Teacher attempts
# per seed (paper Sec. 4.1). Writes the reference to outputs/vera_e/specs.jsonl,
# refreshed after every round.
# Resumable: Teacher generations are cached in outputs/vera_e/teacher_cache.jsonl;
# with the cache present, adding `--replay_only` rebuilds the outputs on CPU.
# Optional: VARIANTS_OUT=<dir> also writes the comparison variants
# (vera_e_1try, vera_e_seed1, vera_e_xcheck) under <dir>, outside outputs/.

set -euo pipefail
cd /home/user
args=(--max_attempts "${MAX_ATTEMPTS:-20}")
if [ -n "${VARIANTS_OUT:-}" ]; then args+=(--variants_out "$VARIANTS_OUT"); fi
python -m method.vera.synthesize "${args[@]}"
