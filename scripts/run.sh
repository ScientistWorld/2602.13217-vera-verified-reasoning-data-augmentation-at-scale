#!/bin/bash
# Job script executed by the scheduler inside the container. This runs the
# offline VeRA reproduction and evaluator from already-present workspace files.

set -euo pipefail

cd /home/user
bash scripts/reproduce.sh
