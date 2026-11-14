#!/bin/bash
# Job entrypoint (runs inside the container, no internet): reproduce the
# reference end to end and refresh train / test scores.
# The hardening checks (variants and shortcuts through the hidden test) are
# reproduced with:
#   VARIANTS_OUT=tmp/hardening/outputs bash scripts/method.sh
#   bash redteam/hardening/run_checks.sh

set -euo pipefail
cd /home/user
nvidia-smi || true
python -c "import torch, transformers; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'transformers', transformers.__version__)"
bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
