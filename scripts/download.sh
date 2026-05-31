#!/bin/bash
# Download datasets and model weights.
#
# Estimated download size: 0 MB for this offline reproduction.
# Estimated disk usage after extraction: 0 MB. The upstream VeRA release is
# cloned under method/VeRA and contains the referenced CSV/generator artifacts.

set -euo pipefail

cd /home/user
mkdir -p data/downloads
echo "No external downloads are required for the packaged offline VeRA reproduction."
