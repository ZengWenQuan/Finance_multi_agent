#!/usr/bin/env bash
set -euo pipefail

# 用法:
#   bash download_qwen3_5_9b.sh
#   bash download_qwen3_5_9b.sh Qwen/Qwen3.5-9B /path/to/save
#
# 环境变量:
#   HF_TOKEN=xxxx                 可选，私有或限流场景建议设置
#   HF_HUB_ENABLE_HF_TRANSFER=1  可选，启用更快下载

MODEL_ID="${1:-Qwen/Qwen3.5-9B}"
TARGET_DIR="${2:-/home/irving/workspace/agent_demo/models/Qwen3.5-9B}"

echo "Model ID   : ${MODEL_ID}"
echo "Target dir : ${TARGET_DIR}"

mkdir -p "${TARGET_DIR}"

if [[ -n "${HF_TOKEN:-}" ]]; then
  export HF_TOKEN
fi

export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

download_with_hf() {
  if hf download --help 2>/dev/null | grep -q -- "--local-dir-use-symlinks"; then
    hf download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}" \
      --local-dir-use-symlinks False
  else
    hf download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}"
  fi
}

download_with_huggingface_cli() {
  if huggingface-cli download --help 2>/dev/null | grep -q -- "--local-dir-use-symlinks"; then
    huggingface-cli download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}" \
      --local-dir-use-symlinks False
  else
    huggingface-cli download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}"
  fi
}

download_with_python_module() {
  if python3 -m huggingface_hub download --help 2>/dev/null | grep -q -- "--local-dir-use-symlinks"; then
    python3 -m huggingface_hub download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}" \
      --local-dir-use-symlinks False
  else
    python3 -m huggingface_hub download "${MODEL_ID}" \
      --repo-type model \
      --local-dir "${TARGET_DIR}"
  fi
}

if command -v hf >/dev/null 2>&1; then
  echo "Using downloader: hf"
  download_with_hf
elif command -v huggingface-cli >/dev/null 2>&1; then
  echo "Using downloader: huggingface-cli"
  download_with_huggingface_cli
elif command -v python3 >/dev/null 2>&1; then
  echo "Using downloader: python3 -m huggingface_hub"
  download_with_python_module
else
  echo "Error: neither 'hf', 'huggingface-cli', nor 'python3' is available."
  exit 1
fi

echo "Download completed: ${TARGET_DIR}"
echo
echo "Examples:"
echo "  Official model : bash $0 Qwen/Qwen3.5-9B ${TARGET_DIR}"
echo "  AWQ variant    : bash $0 QuantTrio/Qwen3.5-9B-AWQ /home/irving/workspace/agent_demo/models/Qwen3.5-9B-AWQ"
