#!/bin/bash
# Score every method directory under outputs/ on the visible train split.
# Writes scoring/scores_train.json. Takes no arguments.

set -euo pipefail
cd /home/user
python eval/train/evaluate.py
