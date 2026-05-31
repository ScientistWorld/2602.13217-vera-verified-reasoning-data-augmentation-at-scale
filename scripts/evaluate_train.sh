#!/bin/bash
# Evaluate visible train-slice method outputs and write scoring/scores_train.json.

set -euo pipefail

cd /home/user

args=(
  --artifacts-root "${ARTIFACTS_ROOT:-outputs}"
  --scores scoring/scores_train.json
)

if [[ -n "${ARTIFACT_DIR:-}" ]]; then
  args+=(--artifacts "$ARTIFACT_DIR")
fi

python eval/train/evaluate.py "${args[@]}"
