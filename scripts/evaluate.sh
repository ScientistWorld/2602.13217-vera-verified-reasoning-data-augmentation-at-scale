#!/bin/bash
# Score every method under outputs/ on the visible train split and write
# scoring/scores.json (same protocol as scripts/evaluate_train.sh).

set -euo pipefail
cd /home/user
python eval/train/evaluate.py --scores scoring/scores.json
