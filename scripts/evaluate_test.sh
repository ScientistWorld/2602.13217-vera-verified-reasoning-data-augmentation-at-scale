#!/bin/bash
# Score every method directory under outputs/ on the hidden test split.
# Writes scoring/scores_test.json. Takes no arguments; every subdirectory of
# outputs/ (except names starting with "_" or ".") is scored, and a directory
# without a readable specs.jsonl is scored as a failed run.

set -euo pipefail
cd /home/user
python eval/test/evaluate.py
