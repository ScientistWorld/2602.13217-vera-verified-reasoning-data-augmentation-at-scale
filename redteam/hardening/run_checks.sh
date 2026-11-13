#!/bin/bash
# Hardening check (CPU): score the reference, its better / weaker variants, the
# baselines and the shortcut submissions through the hidden-test evaluator,
# before and after the hardening fixes, and rank them with
# scoring/reference.json.
#
# Needs: outputs/{vera_e,label_copy,expression_search} (scripts/run.sh) and the
# variants written by `VARIANTS_OUT=tmp/hardening/outputs bash scripts/method.sh`.
# "Before" needs tmp/hardening/before/ (pre-hardening outputs and a copy of the
# pre-hardening evaluator, kept out of git); it is skipped when absent.
# Results: tmp/hardening/scores_*.json and redteam/hardening/results/.

set -euo pipefail
cd /home/user
H=tmp/hardening
RES=redteam/hardening/results
mkdir -p "$RES"

build_cohort() {  # $1 = cohort dir, $2 = reference outputs root, $3 = variants root
  local dir=$1 src=$2 var=$3
  rm -rf "$dir"
  mkdir -p "$dir"
  for m in vera_e label_copy expression_search; do ln -s "$PWD/$src/$m" "$dir/$m"; done
  for m in vera_e_1try vera_e_seed1 vera_e_xcheck; do
    if [ -d "$var/$m" ]; then ln -s "$PWD/$var/$m" "$dir/$m"; fi
  done
  python redteam/hardening/build_shortcuts.py --reference "$src/vera_e/specs.jsonl" \
    --expression "$src/expression_search/specs.jsonl" --xcheck "$var/vera_e_xcheck/specs.jsonl" --out "$dir"
  cp -r "$H/consensus/sc_consensus_bruteforce" "$dir/"
}

# Stronger brute force (shared by both cohorts; needs no Teacher).
python redteam/hardening/consensus_bruteforce.py --out "$H/consensus/sc_consensus_bruteforce" \
  --seeds data/gsm8k_vera/train_seeds.jsonl data/gsm8k_vera/test_seeds.jsonl

# After: final evaluator, final reference (20 Teacher attempts) and variants.
build_cohort "$H/after_outputs" outputs "$H/outputs"
if [ -d "$H/before/outputs/vera_e" ]; then ln -s "$PWD/$H/before/outputs/vera_e" "$H/after_outputs/vera_e_6try"; fi
python eval/test/evaluate.py --outputs "$H/after_outputs" --scores "$H/scores_test_after.json"
python eval/train/evaluate.py --outputs "$H/after_outputs" --scores "$H/scores_train_after.json"
cp "$H/scores_test_after.json" "$H/scores_train_after.json" "$RES/"
files=("$H/scores_test_after.json" "$H/scores_train_after.json")

# Before: pre-hardening evaluator on the pre-hardening (6-attempt) outputs.
if [ -f "$H/before/eval_test/evaluate.py" ] && [ -d "$H/before/outputs/vera_e" ]; then
  build_cohort "$H/before_outputs" "$H/before/outputs" "$H/before/outputs"
  python "$H/before/eval_test/evaluate.py" --outputs "$H/before_outputs" --scores "$H/scores_test_before.json"
  cp "$H/scores_test_before.json" "$RES/"
  files+=("$H/scores_test_before.json")
fi

python redteam/hardening/rank.py "${files[@]}" --json "$RES/summary.json" | tee "$RES/summary.txt"
