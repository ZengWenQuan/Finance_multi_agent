#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="/home/irving/workspace/agent_demo"
DATA_DIR="${PROJECT_ROOT}/data"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate lamost

mkdir -p "${DATA_DIR}/risk_nasdaq"
mkdir -p "${DATA_DIR}/nasdaq_news_sentiment"

HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download \
  benstaf/risk_nasdaq \
  --repo-type dataset \
  --local-dir "${DATA_DIR}/risk_nasdaq"

HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download \
  benstaf/nasdaq_news_sentiment \
  --repo-type dataset \
  --local-dir "${DATA_DIR}/nasdaq_news_sentiment"

echo "Download complete."
