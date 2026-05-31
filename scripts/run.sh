#!/bin/bash
# Job script executed by the scheduler inside the container. This scores the
# visible train slice and held-out test slice from existing method artifacts.

set -euo pipefail

cd /home/user
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
