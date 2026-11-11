#!/bin/bash
# Install Python packages into the container overlay (system Python, no venv).
# torch wheels from PyPI bundle the CUDA runtime; transformers runs the Teacher.
set -e
uv pip install --system "torch==2.5.1" "transformers==4.46.3" "accelerate==1.1.1" "safetensors>=0.4.5" "sentencepiece" "datasets" "requests" "tqdm"
