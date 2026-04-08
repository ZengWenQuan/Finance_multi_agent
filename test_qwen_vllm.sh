#!/usr/bin/env bash
set -u

BASE_URL="${1:-http://127.0.0.1:8000}"
MODEL_NAME="${2:-qwen3.5-tiny}"
CHAT_PAYLOAD='{"model":"'"${MODEL_NAME}"'","messages":[{"role":"user","content":"Reply with exactly: ok"}],"temperature":0,"max_tokens":8}'

print_section() {
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

print_section "Config"
echo "BASE_URL   : ${BASE_URL}"
echo "MODEL_NAME : ${MODEL_NAME}"

print_section "Proxy Env"
env | grep -i proxy || true

print_section "Process Check"
run_cmd ps -ef

print_section "Port 8000 Check"
run_cmd ss -ltnp

print_section "Health Via Current Env"
run_cmd curl -i -sS -m 15 "${BASE_URL}/health"

print_section "Models Via Current Env"
run_cmd curl -i -sS -m 20 "${BASE_URL}/v1/models"

print_section "Chat Via Current Env"
run_cmd curl -i -sS -m 60 "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "${CHAT_PAYLOAD}"

print_section "Health Bypass Proxy"
run_cmd curl --noproxy '*' -i -sS -m 15 "${BASE_URL}/health"

print_section "Models Bypass Proxy"
run_cmd curl --noproxy '*' -i -sS -m 20 "${BASE_URL}/v1/models"

print_section "Chat Bypass Proxy"
run_cmd curl --noproxy '*' -i -sS -m 60 "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "${CHAT_PAYLOAD}"

print_section "Health With Explicit NO_PROXY"
run_cmd env NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  curl --noproxy 127.0.0.1 -i -sS -m 15 "${BASE_URL}/health"

print_section "Models With Explicit NO_PROXY"
run_cmd env NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  curl --noproxy 127.0.0.1 -i -sS -m 20 "${BASE_URL}/v1/models"

print_section "Chat With Explicit NO_PROXY"
run_cmd env NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
  curl --noproxy 127.0.0.1 -i -sS -m 60 "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "${CHAT_PAYLOAD}"

print_section "Done"
echo "If 'Current Env' returns 502 but 'Bypass Proxy' returns 200, the local proxy is intercepting requests."
echo "If both proxy-bypass tests return connection refused, vLLM is not listening or is not ready yet."
