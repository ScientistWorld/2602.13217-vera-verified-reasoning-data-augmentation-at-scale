#!/bin/bash
# Job script executed by the scheduler inside the container. This reruns the
# packaged reproduction, then refreshes the visible train and held-out test
# split scores from the resulting method artifacts.

set -euo pipefail

cd /home/user
bash scripts/reproduce.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
