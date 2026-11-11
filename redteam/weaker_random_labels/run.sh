#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit --case weaker_random_labels
