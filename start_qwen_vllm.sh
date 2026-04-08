#!/bin/bash
set -u

ROOT_DIR="/home/irving/workspace/agent_demo"
LOG_DIR="${ROOT_DIR}/logs/vllm"
PID_FILE="${LOG_DIR}/qwen_vllm.pid"
LATEST_LOG_LINK="${LOG_DIR}/latest.log"
MODEL_DIR="${ROOT_DIR}/Qwen3.5-Tiny"
HOST="0.0.0.0"
PORT="8000"
MODEL_NAME="qwen3.5-tiny"
STARTUP_TIMEOUT_SEC="${STARTUP_TIMEOUT_SEC:-1800}"
POLL_INTERVAL_SEC=2

mkdir -p "${LOG_DIR}"

if [[ -f "${PID_FILE}" ]]; then
  existing_pid="$(cat "${PID_FILE}")"
  if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
    echo "vLLM is already running with PID ${existing_pid}"
    echo "Health URL: http://${HOST}:${PORT}/health"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/vllm_${timestamp}.log"
ln -sfn "${LOG_FILE}" "${LATEST_LOG_LINK}"

# 1. 环境激活：激活安装了 vllm 的 sft Conda 环境
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate sft

# 2. 标准库兼容性：解决 WSL 环境中 libstdc++.so 库版本过低的问题
export LD_LIBRARY_PATH="$(find "$(conda info --base)/envs/sft/lib" -name "libstdc++.so.6" -exec dirname {} \; | head -n 1):${LD_LIBRARY_PATH:-}"

# 3. WSL 网络与驱动优化
export VLLM_HOST_IP=127.0.0.1
export NCCL_P2P_DISABLE=1
export NCCL_IB_DISABLE=1

# 4. 清理代理环境，确保本地请求不经过代理
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost

nohup setsid python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_DIR}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --served-model-name "${MODEL_NAME}" \
    --trust-remote-code \
    --language-model-only \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_xml \
    --gpu-memory-utilization 0.5 \
    --max-model-len 32768 \
    --enforce-eager \
    > "${LOG_FILE}" 2>&1 < /dev/null &

server_pid=$!
disown "${server_pid}" 2>/dev/null || true
echo "${server_pid}" > "${PID_FILE}"

echo "Starting vLLM in background..."
echo "PID     : ${server_pid}"
echo "Log file: ${LOG_FILE}"

elapsed=0
while (( elapsed < STARTUP_TIMEOUT_SEC )); do
  if ! kill -0 "${server_pid}" 2>/dev/null; then
    echo "vLLM exited before becoming ready."
    echo "Last log lines:"
    tail -n 80 "${LOG_FILE}" || true
    rm -f "${PID_FILE}"
    exit 1
  fi

  if curl --noproxy '*' -fsS -m 5 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    echo "vLLM is ready."
    echo "Health URL: http://${HOST}:${PORT}/health"
    echo "Model API : http://${HOST}:${PORT}/v1/models"
    exit 0
  fi

  sleep "${POLL_INTERVAL_SEC}"
  elapsed=$((elapsed + POLL_INTERVAL_SEC))
done

echo "vLLM did not become ready within ${STARTUP_TIMEOUT_SEC}s."
echo "Stopping PID ${server_pid}."
kill "${server_pid}" 2>/dev/null || true
sleep 2
if kill -0 "${server_pid}" 2>/dev/null; then
  kill -9 "${server_pid}" 2>/dev/null || true
fi
rm -f "${PID_FILE}"
echo "Last log lines:"
tail -n 80 "${LOG_FILE}" || true
exit 1
