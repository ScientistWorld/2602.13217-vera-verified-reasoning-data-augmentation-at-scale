#!/bin/bash
# End-to-end reproduction: download, Teacher synthesis (GPU), baselines, scoring.

set -euo pipefail
cd /home/user
bash scripts/download.sh
bash scripts/method.sh
bash scripts/baseline.sh
bash scripts/evaluate.sh
