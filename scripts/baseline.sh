#!/bin/bash
# Run a trivial random-answer baseline against generated variants.

set -euo pipefail

cd /home/user
if [ ! -e outputs/vera_repro/variants.jsonl ]; then
  bash scripts/method.sh
fi
python baseline/random_answer.py \
  --source outputs/vera_repro/variants.jsonl \
  --out outputs/baseline/random_predictions.jsonl
