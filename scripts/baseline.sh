#!/bin/bash
# Baseline spec writers (CPU): naive label copying and brute-force expression search.

set -euo pipefail
cd /home/user/baseline
python label_copy.py --out ../outputs/label_copy \
  --seeds ../data/gsm8k_vera/train_seeds.jsonl ../data/gsm8k_vera/test_seeds.jsonl
python expression_search.py --out ../outputs/expression_search \
  --seeds ../data/gsm8k_vera/train_seeds.jsonl ../data/gsm8k_vera/test_seeds.jsonl
