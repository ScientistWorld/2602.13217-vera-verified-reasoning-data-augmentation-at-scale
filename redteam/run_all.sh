#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.audit
python -m redteam.summarize
