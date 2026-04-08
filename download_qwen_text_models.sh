#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="/home/irving/workspace/agent_demo"
MODEL_DIR="${PROJECT_ROOT}/models"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate lamost

mkdir -p "${MODEL_DIR}/Qwen3-0.6B-Base"

huggingface-cli download \
  Qwen/Qwen3-0.6B-Base \
  --local-dir "${MODEL_DIR}/Qwen3-0.6B-Base"

echo "Download complete."
