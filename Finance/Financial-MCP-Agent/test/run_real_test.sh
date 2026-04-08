#!/bin/bash
# ============================================================
#  Financial-MCP-Agent 单独 Agent 测试脚本
#
#  用法:
#    bash test/run_real_test.sh                         # 默认: 测试 fundamental agent
#    bash test/run_real_test.sh fundamental             # 测试基本面分析
#    bash test/run_real_test.sh technical               # 测试技术分析
#    bash test/run_real_test.sh value                   # 测试估值分析
#    bash test/run_real_test.sh news                    # 测试新闻分析
#    bash test/run_real_test.sh summary                 # 测试汇总报告
#    bash test/run_real_test.sh all                     # 依次测试全部 5 个 Agent
#    bash test/run_real_test.sh fundamental "比亚迪" "比亚迪" "002594"  # 自定义参数
# ============================================================

# 1. 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit

# 2. 激活 Conda 环境 (强制使用 lamost)
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -z "$CONDA_BASE" ]; then
    echo "❌ 找不到 conda，请确保 conda 已安装并设置在 PATH 中。"
    exit 1
fi
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate lamost || { echo "❌ 激活 lamost 环境失败，请检查环境是否存在。"; exit 1; }

# 3. 加载环境变量 (如有 .env 文件)
if [ -f .env ]; then
    set -a
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        # 跳过包含中文注释的行
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        export "$key=$value"
    done < .env
    set +a
    export OPENAI_COMPATIBLE_BASE_URL="http://127.0.0.1:8000/v1"
fi

# 4. 清理代理环境变量，防止本地 127.0.0.1 请求被转发
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost

# 5. 延长超时时间
export AGENT_TEST_TIMEOUT_SECONDS=300

# 6. 解析参数
AGENT=${1:-fundamental}
QUERY=${2:-"分析比亚迪股票怎么样"}
COMPANY=${3:-"比亚迪"}
CODE=${4:-"002594"}

# 如果第二个参数是 agent 名称（不是 query），做兼容处理
if [[ "$AGENT" != "fundamental" && "$AGENT" != "technical" && "$AGENT" != "value" && "$AGENT" != "news" && "$AGENT" != "summary" && "$AGENT" != "all" ]]; then
    # 第一个参数不是 agent 名称，当作 query
    QUERY=${1:-"分析比亚迪股票怎么样"}
    AGENT=fundamental
fi

echo "══════════════════════════════════"
echo "  单独 Agent 测试"
echo "  Agent:     $AGENT"
echo "  查询内容:  $QUERY"
echo "  识别公司:  $COMPANY"
echo "  证券代码:  $CODE"
echo "  当前时间:  $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════"

# 7. 执行测试
python test/run_single_agent_test.py --agent "$AGENT" --query "$QUERY" --company "$COMPANY" --code "$CODE"

# 8. 处理结果
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ [SUCCESS] Agent $AGENT 测试通过！"
    echo "  结果预览：详见 test/report/ 目录下的 markdown 文件。"
else
    echo "❌ [FAILED] Agent $AGENT 测试失败。"
    echo "  失败详情：请查看 test/report/single_test_failures.txt"
fi

echo "══════════════════════════════════"
exit $EXIT_CODE
