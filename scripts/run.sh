#!/bin/bash
# Job script executed by the scheduler inside the container.

set -euo pipefail

cd /home/user
bash scripts/reproduce.sh
