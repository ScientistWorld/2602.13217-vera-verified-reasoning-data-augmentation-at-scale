#!/bin/bash
# VeRA-E spec synthesis with the Teacher LLM (GPU). Writes outputs/vera_e,
# outputs/vera_e_1try and outputs/vera_e_xcheck (each with specs.jsonl).
# Resumable: Teacher generations are cached in outputs/_teacher_cache/.

set -euo pipefail
cd /home/user
python -m method.vera.synthesize --max_attempts "${MAX_ATTEMPTS:-20}"
