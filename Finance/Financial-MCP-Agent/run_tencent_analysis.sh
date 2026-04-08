#!/bin/bash
set -euo pipefail

PROJECT_DIR="/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent"
QUERY="${1:-我想了解一下腾讯的投资价值}"

cd "${PROJECT_DIR}"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate lamost

python src/main.py --command "${QUERY}"
