#!/usr/bin/env bash
# ============================================================
#  start.sh — Financial MCP Agent 启动脚本
#
#  用法：
#    bash deploy/start.sh          # 普通启动（镜像已存在时跳过构建）
#    bash deploy/start.sh --build  # 强制重新构建后端镜像
#    bash deploy/start.sh --down   # 停止并移除所有容器
#    bash deploy/start.sh --logs   # 查看实时日志
#    bash deploy/start.sh --status # 查看容器状态
#
#  运行位置：任意目录均可，脚本会自动定位到项目根
# ============================================================

set -euo pipefail

# ---------- 路径定位 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"       # Financial-MCP-Agent/
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${PROJECT_ROOT}/.env"

# ---------- 颜色 ----------
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[0;34m' N='\033[0m'
info()  { echo -e "${G}[✓]${N} $*"; }
warn()  { echo -e "${Y}[!]${N} $*"; }
error() { echo -e "${R}[✗]${N} $*" >&2; exit 1; }
title() { echo -e "\n${B}══════════════════════════════════${N}"; echo -e "${B}  $*${N}"; echo -e "${B}══════════════════════════════════${N}"; }

# ---------- 参数解析 ----------
CMD="${1:-start}"
case "$CMD" in
  --build)  CMD="build"  ;;
  --down)   CMD="down"   ;;
  --logs)   CMD="logs"   ;;
  --status) CMD="status" ;;
  --help|-h)
    sed -n '3,11p' "$0" | sed 's/#  //'
    exit 0
    ;;
esac

# ---------- 功能：查看日志 ----------
if [ "$CMD" = "logs" ]; then
  echo "按 Ctrl+C 退出日志..."
  docker-compose -f "${COMPOSE_FILE}" logs -f --tail=100
  exit 0
fi

# ---------- 功能：查看状态 ----------
if [ "$CMD" = "status" ]; then
  docker-compose -f "${COMPOSE_FILE}" ps
  exit 0
fi

# ---------- 功能：停止服务 ----------
if [ "$CMD" = "down" ]; then
  title "停止服务"
  docker-compose -f "${COMPOSE_FILE}" down
  info "服务已停止，数据目录保留在 data/ reports/ logs/"
  exit 0
fi

# ============================================================
#  主流程：启动 / 构建
# ============================================================
title "Financial MCP Agent 启动"

# ---- Step 1: 检查 docker ----
echo ""
echo "  [1/5] 检查 Docker 环境..."
command -v docker &>/dev/null        || error "未找到 docker，请先安装 Docker Desktop 或 Docker Engine"
docker info &>/dev/null 2>&1         || error "Docker daemon 未运行，请启动 Docker"
if command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
elif docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  error "未找到 docker-compose 插件"
fi
info "Docker 环境正常"

# ---- Step 2: 检查 .env ----
echo ""
echo "  [2/5] 检查配置文件..."
if [ ! -f "${ENV_FILE}" ]; then
  warn ".env 不存在，从 .env.example 复制..."
  cp "${PROJECT_ROOT}/.env.example" "${ENV_FILE}"
  warn "请编辑 ${ENV_FILE} 填写 API Key 后重新运行"
  exit 1
fi

# 检查 API Key 是否还是占位符
API_KEY=$(grep -E "^OPENAI_COMPATIBLE_API_KEY=" "${ENV_FILE}" | cut -d= -f2- | tr -d '"' || true)
if [ -z "${API_KEY}" ] || [ "${API_KEY}" = "your_openai_compatible_api_key" ]; then
  error "OPENAI_COMPATIBLE_API_KEY 未设置，请编辑 ${ENV_FILE}"
fi
info "配置文件检查通过"

# ---- Step 3: 准备目录 ----
echo ""
echo "  [3/5] 准备数据目录..."
mkdir -p "${PROJECT_ROOT}/data"
mkdir -p "${PROJECT_ROOT}/reports"
mkdir -p "${PROJECT_ROOT}/logs"
info "目录就绪：data/ reports/ logs/"

# ---- Step 4: 构建镜像 ----
echo ""
echo "  [4/5] 准备镜像..."
if [ "$CMD" = "build" ]; then
  warn "强制重新构建后端镜像（--build 模式）..."
  $COMPOSE_CMD -f "${COMPOSE_FILE}" build --no-cache backend
  info "镜像构建完成"
elif ! docker image inspect financial-mcp-backend:latest &>/dev/null 2>&1; then
  warn "未找到后端镜像，自动构建..."
  $COMPOSE_CMD -f "${COMPOSE_FILE}" build backend
  info "镜像构建完成"
else
  info "镜像已存在，跳过构建（传 --build 可强制重建）"
fi

# ---- Step 5: 启动服务 ----
echo ""
echo "  [5/5] 启动服务..."
$COMPOSE_CMD -f "${COMPOSE_FILE}" up -d

# 等待后端健康检查通过
echo ""
echo "  等待后端启动（最长 60s）..."
MAX=30; COUNT=0
while [ $COUNT -lt $MAX ]; do
  if $COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T backend \
      curl -sf http://localhost:8000/api/health &>/dev/null 2>&1; then
    break
  fi
  sleep 2; COUNT=$((COUNT+1))
  printf "\r  等待中... %ds" $((COUNT*2))
done
echo ""

if [ $COUNT -ge $MAX ]; then
  warn "后端启动超时，查看日志排查："
  warn "  $COMPOSE_CMD -f ${COMPOSE_FILE} logs backend"
  exit 1
fi

# ---------- 获取真实局域网 IP ----------
HOST_IP=$(hostname -I 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ && $i !~ /^172\./ && $i !~ /^198\./ && $i !~ /^10\.10\./ && $i !~ /^10\.42\./) {print $i; exit}}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="127.0.0.1"
fi

# ---------- 成功汇报 ----------
title "启动成功 🎉"
echo ""
echo "  前端页面：  http://${HOST_IP}:8890"
echo "  API 文档：  http://${HOST_IP}:8890/api/docs"
echo "  健康检查：  http://${HOST_IP}:8890/api/health"
echo ""
echo "  查看日志：  bash deploy/start.sh --logs"
echo "  查看状态：  bash deploy/start.sh --status"
echo "  停止服务：  bash deploy/stop.sh"
echo ""
