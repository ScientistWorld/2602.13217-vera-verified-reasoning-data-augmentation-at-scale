#!/bin/bash
# Evaluate held-out test-slice method outputs and write scoring/scores_test.json.

set -euo pipefail

cd /home/user

args=(
  --artifacts-root "${ARTIFACTS_ROOT:-outputs}"
  --method-list scoring/scores_train.json
  --scores scoring/scores_test.json
)

if [[ -n "${ARTIFACT_DIR:-}" ]]; then
  args+=(--artifacts "$ARTIFACT_DIR")
fi

python eval/test/evaluate.py "${args[@]}"
