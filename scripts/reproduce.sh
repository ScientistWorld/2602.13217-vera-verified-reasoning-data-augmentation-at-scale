#!/bin/bash
# End-to-end reproduction script.

set -euo pipefail

cd /home/user
bash scripts/download.sh
bash scripts/method.sh
bash scripts/evaluate.sh
