#!/bin/bash
# Fetch every external artifact this gym needs into data/downloads/ (idempotent).
#
#   data/downloads/Qwen2.5-7B-Instruct   Teacher LLM for VeRA spec synthesis (~15 GB)
#                                        https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
#
# The seed files (data/gsm8k_vera/*.jsonl) are derived from GSM8K
# (github.com/openai/grade-school-math, MIT) and committed to git; they need no
# download.

set -euo pipefail
cd /home/user

MODEL_DIR=data/downloads/Qwen2.5-7B-Instruct
MODEL_URL=https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/resolve/main
mkdir -p "$MODEL_DIR"
for f in LICENSE config.json generation_config.json merges.txt model.safetensors.index.json \
         tokenizer.json tokenizer_config.json vocab.json \
         model-00001-of-00004.safetensors model-00002-of-00004.safetensors \
         model-00003-of-00004.safetensors model-00004-of-00004.safetensors; do
  if [ ! -s "$MODEL_DIR/$f" ]; then
    echo "downloading $f"
    wget -q -O "$MODEL_DIR/$f.part" "$MODEL_URL/$f"
    mv "$MODEL_DIR/$f.part" "$MODEL_DIR/$f"
  fi
done
echo "download.sh: all artifacts present"
