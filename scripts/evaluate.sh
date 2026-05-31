#!/bin/bash
# Evaluate method outputs and write scoring/scores.json.

set -euo pipefail

cd /home/user
python eval/evaluate_vera_outputs.py \
  --artifacts "${ARTIFACT_DIR:-outputs/vera_repro}" \
  --scores scoring/scores.json
