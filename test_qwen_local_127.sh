#!/usr/bin/env bash
set -u

BASE_URL="${1:-http://127.0.0.1:8000}"
MODEL_NAME="${2:-qwen3.5-tiny}"
CHAT_PAYLOAD='{"model":"'"${MODEL_NAME}"'","messages":[{"role":"user","content":"Reply with exactly: ok"}],"temperature":0,"max_tokens":8}'

section() {
  echo
  echo "==== $1 ===="
}

run_cmd() {
  echo "+ $*"
  "$@"
  local status=$?
  echo
  echo "[exit_code] ${status}"
  return 0
}

section "Config"
echo "BASE_URL   : ${BASE_URL}"
echo "MODEL_NAME : ${MODEL_NAME}"

section "Health"
run_cmd curl --noproxy '*' -i -sS -m 15 "${BASE_URL}/health"

section "Models"
run_cmd curl --noproxy '*' -i -sS -m 20 "${BASE_URL}/v1/models"

section "Chat"
run_cmd curl --noproxy '*' -i -sS -m 60 "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "${CHAT_PAYLOAD}"

section "Done"
echo "If Health/Models/Chat all return 200, local 127.0.0.1 access is working."
