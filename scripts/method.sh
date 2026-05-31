#!/bin/bash
# Run the paper's method reproduction and write scoreable artifacts.

set -euo pipefail

cd /home/user
python -m method.vera_repro.run_geometry_repro \
  --out_dir outputs/vera_repro \
  --samples_per_spec "${SAMPLES_PER_SPEC:-8}" \
  --base_seed "${BASE_SEED:-0}"
