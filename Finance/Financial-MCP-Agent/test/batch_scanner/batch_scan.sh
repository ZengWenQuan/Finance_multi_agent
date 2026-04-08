#!/bin/bash
# ============================================================
#  Financial-MCP-Agent 全自动股票扫描器 (RAG 数据生成器)
# ============================================================

PROJECT_ROOT="/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent"
cd "$PROJECT_ROOT" || exit
source /root/miniconda3/etc/profile.d/conda.sh
conda activate lamost

# 设置 Docker 域名映射（以便在宿主机运行）
export OPENAI_COMPATIBLE_BASE_URL="http://127.0.0.1:8000/v1"
# 清理代理
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
export NO_PROXY=127.0.0.1,localhost

LIST_FILE="test/batch_scanner/scan_list.txt"
FAILURE_LOG="test/batch_scanner/scan_failures.log"

# 如果没有列表文件，我们先在这里放一个 SSE50 和 SZSE50 的示例核心列表
# 你可以稍后自己修改或通过 python test/get_index_list.py > test/scan_list.txt 补充
if [ ! -f "$LIST_FILE" ]; then
    echo "sh.600519,贵州茅台" > "$LIST_FILE"
    echo "sh.601318,中国平安" >> "$LIST_FILE"
    echo "sh.600036,招商银行" >> "$LIST_FILE"
    echo "sh.600276,恒瑞医药" >> "$LIST_FILE"
    echo "sh.600487,亨通光电" >> "$LIST_FILE"
    echo "sh.601857,中国石油" >> "$LIST_FILE"
    echo "sh.601398,工商银行" >> "$LIST_FILE"
    echo "sh.600900,长江电力" >> "$LIST_FILE"
    echo "sh.600030,中信证券" >> "$LIST_FILE"
    echo "sh.600309,万华化学" >> "$LIST_FILE"
fi

echo "══════════════════════════════════"
echo "  🚀 启动全量扫描器"
echo "  列表位置: $LIST_FILE"
echo "  待处理量: $(wc -l < "$LIST_FILE")"
echo "══════════════════════════════════"

while IFS=',' read -r code name; do
    # 清理行尾空白
    code=$(echo "$code" | xargs)
    name=$(echo "$name" | xargs)
    
    [ -z "$code" ] && continue
    
    # 提取纯代码部分 (如 600487)
    code_pure=$(echo "$code" | cut -d'.' -f2)
    
    # 检查 reports_batch 目录是否已有该股票报告
    if ls reports_batch/report_*_"$code_pure"_*md 1> /dev/null 2>&1 || ls reports/report_*_"$code_pure"_*md 1> /dev/null 2>&1; then
        echo "✅ [SKIP] $name ($code) 跳过（报告已存在）。"
        continue
    fi
    
    echo ""
    echo "----------------------------------------------------"
    echo "⚡ 正在分析: $name ($code) -> 目标: reports_batch/"
    echo "   分析时间: $(date '+%H:%M:%S')"
     
    # 执行分析
    python test/run_real_agents.py \
        --query "请针对 $name ($code) 进行详细的金融基本面和新闻舆情分析，生成专业投资报告。" \
        --company "$name" \
        --code "$code"
    
    SUCCESS=$?
    
    if [ $SUCCESS -eq 0 ]; then
        # 搬家逻辑：找到刚刚生成的报告
        # 我们找最近10秒内生成的、文件名包含该代码的文件
        NEW_REPORT=$(ls -t reports/report_*_"$code_pure"_*md 2>/dev/null | head -n 1)
        if [ -n "$NEW_REPORT" ]; then
            mv "$NEW_REPORT" reports_batch/
            echo "✔️ [SUCCESS] $name ($code) 分析完成，报告已存入 reports_batch/。"
        else
            echo "⚠️ [WARN] $name 分析成功但未找到报告文件。"
        fi
        sleep 3
    else
        echo "❌ [ERROR] $name ($code) 失败。记录到 $FAILURE_LOG。"
        echo "$code,$name,$(date '+%Y-%m-%d %H:%M:%S')" >> "$FAILURE_LOG"
        sleep 5
    fi
    
done < "$LIST_FILE"

echo ""
echo "══════════════════════════════════"
echo "  🏁 所有扫描任务已结束。"
echo "══════════════════════════════════"
