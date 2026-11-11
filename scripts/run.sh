#!/bin/bash
# Temporary audit job entrypoint; restored after the audit.

set -euo pipefail

cd /home/user
bash redteam/run_all.sh
