#!/bin/bash
# ============================================================
#  测试 technical_agent (技术分析)
#
#  用法:
#    bash test/test_technical_agent.sh                          # 默认参数
#    bash test/test_technical_agent.sh "分析比亚迪技术面" "比亚迪" "002594"  # 自定义参数
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit

# 激活 Conda 环境
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "❌ 找不到 conda"
    exit 1
fi
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate lamost || { echo "❌ 激活 lamost 环境失败"; exit 1; }

# 加载环境变量
if [ -f .env ]; then
    set -a
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        export "$key=$value"
    done < .env
    set +a
fi

# 清理代理
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost

# 超时
export AGENT_TEST_TIMEOUT_SECONDS=300

# 参数
QUERY=${1:-"分析比亚迪股票技术面"}
COMPANY=${2:-"比亚迪"}
CODE=${3:-"002594"}

echo "══════════════════════════════════"
echo "  [technical_agent] 技术分析"
echo "  查询: $QUERY"
echo "  公司: $COMPANY"
echo "  代码: $CODE"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════"

python test/run_single_agent_test.py --agent technical --query "$QUERY" --company "$COMPANY" --code "$CODE"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ technical_agent 测试通过!"
else
    echo "❌ technical_agent 测试失败"
fi
echo "══════════════════════════════════"
exit $EXIT_CODE
