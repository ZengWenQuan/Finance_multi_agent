#!/usr/bin/env bash
# ============================================================
#  stop.sh — Financial MCP Agent 停止脚本
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# ---------- 颜色 ----------
G='\033[0;32m' B='\033[0;34m' N='\033[0m'
info()  { echo -e "${G}[✓]${N} $*"; }
title() { echo -e "\n${B}══════════════════════════════════${N}"; echo -e "${B}  $*${N}"; echo -e "${B}══════════════════════════════════${N}"; }

# 使用 docker-compose 进行停止
if command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
elif docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo -e "\033[0;31m[✗]\033[0m 未找到 docker-compose 或 docker compose 插件" >&2
  exit 1
fi

title "停止 Financial MCP Agent 服务"
$COMPOSE_CMD -f "${COMPOSE_FILE}" down
info "服务已完全停止"
info "注：数据仍然安全保留在 data/, reports/ 和 logs/ 目录中。"
