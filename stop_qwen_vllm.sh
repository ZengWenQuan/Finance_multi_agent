#!/bin/bash
set -u

ROOT_DIR="/home/irving/workspace/agent_demo"
LOG_DIR="${ROOT_DIR}/logs/vllm"
PID_FILE="${LOG_DIR}/qwen_vllm.pid"
MATCH_PATTERN="python -m vllm.entrypoints.openai.api_server --model ${ROOT_DIR}/Qwen3.5-Tiny"

stop_pid() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 1
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    return 1
  fi

  echo "Stopping PID ${pid}..."
  kill "${pid}" 2>/dev/null || true

  for _ in $(seq 1 15); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done

  echo "PID ${pid} did not exit after SIGTERM, sending SIGKILL."
  kill -9 "${pid}" 2>/dev/null || true
  sleep 1
  ! kill -0 "${pid}" 2>/dev/null
}

stopped=0

if [[ -f "${PID_FILE}" ]]; then
  pid_from_file="$(cat "${PID_FILE}")"
  if stop_pid "${pid_from_file}"; then
    stopped=1
  fi
  rm -f "${PID_FILE}"
fi

fallback_pids="$(pgrep -f "${MATCH_PATTERN}" || true)"
if [[ -n "${fallback_pids}" ]]; then
  for pid in ${fallback_pids}; do
    if stop_pid "${pid}"; then
      stopped=1
    fi
  done
fi

if [[ "${stopped}" -eq 1 ]]; then
  echo "vLLM stopped."
  exit 0
fi

echo "No matching vLLM process found."
exit 0
