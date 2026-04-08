"""
金融分析智能体系统主程序 (Financial Analysis AI Agent System Main Program)

本文件是金融分析智能体系统的核心入口点，实现了以下主要功能：

1. 多智能体工作流管理：使用LangGraph构建并行执行的智能体工作流
2. 命令行界面：提供用户友好的交互式命令行界面
3. 自然语言处理：自动识别和提取股票代码、公司名称
4. 日志系统：完整的执行日志记录和错误处理
5. 报告生成：生成综合性的金融分析报告

工作流程：
start_node → [fundamental_analyst, technical_analyst, value_analyst] → summarizer → END
"""

# ============================================================================
# 导入必要的模块和依赖
# ============================================================================

# 在导入其他模块之前设置环境变量，抑制无用输出
import os
import sys
from pathlib import Path

# 设置环境变量来抑制transformers和其他库的冗余输出
os.environ["TRANSFORMERS_VERBOSITY"] = "error"  # 只显示错误信息
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # 禁用tokenizer并行化警告
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # 减少CUDA相关输出
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"  # 减少内存分配信息

# 设置日志级别，抑制第三方库的INFO级别输出
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# 在导入本项目模块前，确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 日志和状态管理相关导入
from src.utils.logging_config import setup_logger, SUCCESS_ICON, ERROR_ICON, WAIT_ICON
from src.utils.state_definition import AgentState
from src.utils.execution_logger import initialize_execution_logger, finalize_execution_logger, get_execution_logger
from src.services.analysis_service import run_analysis_workflow
from src.services.query_processing import extract_entities_from_query

# LangGraph工作流框架导入
# 环境变量和系统相关导入
from dotenv import load_dotenv
import argparse
import asyncio
import re

# ============================================================================
# 初始化和配置
# ============================================================================

# 设置日志记录器
logger = setup_logger(__name__)

# 已在文件顶部插入项目根目录到 sys.path

# 加载环境变量（从.env文件）
load_dotenv(override=True)

# 调试：打印关键环境变量以验证配置
logger.info(f"Environment Variables Loaded:")
logger.info(
    f"  OPENAI_COMPATIBLE_MODEL: {os.getenv('OPENAI_COMPATIBLE_MODEL', 'Not Set')}")
logger.info(
    f"  OPENAI_COMPATIBLE_BASE_URL: {os.getenv('OPENAI_COMPATIBLE_BASE_URL', 'Not Set')}")
logger.info(
    f"  OPENAI_COMPATIBLE_API_KEY: {'*' * 20 if os.getenv('OPENAI_COMPATIBLE_API_KEY') else 'Not Set'}")

# 重新设置日志记录器（确保正确配置）
logger = setup_logger(__name__)


async def main():
    """
    主函数：金融分析智能体系统的核心执行逻辑
    
    功能包括：
    1. 初始化执行日志系统
    2. 构建LangGraph工作流
    3. 处理命令行参数和用户输入
    4. 提取股票信息（代码、公司名称）
    5. 执行多智能体分析工作流
    6. 生成和保存分析报告
    7. 错误处理和日志记录
    """
    
    # 初始化执行日志系统
    execution_logger = initialize_execution_logger()
    logger.info(
        f"{SUCCESS_ICON} 执行日志系统已初始化，日志目录: {execution_logger.execution_dir}")

    try:
        # ============================================================================
        # 1. 定义LangGraph工作流 
        # ============================================================================
        
        # ============================================================================
        # 2. 实现命令行界面 
        # ============================================================================
        
        # 创建命令行参数解析器
        parser = argparse.ArgumentParser(description="Financial Agent CLI")
        parser.add_argument(
            "--command",
            type=str,
            required=False,  # 改为非必需，支持交互式输入
            help="The user query for financial analysis (e.g., '分析嘉友国际')"
        )
        args = parser.parse_args()

        # 处理用户查询输入
        if args.command:
            # 如果通过命令行参数提供查询
            user_query = args.command
        else:
            # 显示ASCII艺术开屏图像和交互式界面
            print("\n")
            print(
                "╔══════════════════════════════════════════════════════════════════════════════╗")
            print(
                "║                                                                              ║")
            print(
                "║      ███████╗██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗██╗ █████╗ ██╗          ║")
            print(
                "║      ██╔════╝██║████╗  ██║██╔══██╗████╗  ██║██╔════╝██║██╔══██╗██║          ║")
            print(
                "║      █████╗  ██║██╔██╗ ██║███████║██╔██╗ ██║██║     ██║███████║██║          ║")
            print(
                "║      ██╔══╝  ██║██║╚██╗██║██╔══██║██║╚██╗██║██║     ██║██╔══██║██║          ║")
            print(
                "║      ██║     ██║██║ ╚████║██║  ██║██║ ╚████║╚██████╗██║██║  ██║███████╗      ║")
            print(
                "║      ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝╚═╝  ╚═╝╚══════╝      ║")
            print(
                "║                                                                              ║")
            print(
                "║                █████╗  ██████╗ ███████╗███╗   ██╗████████╗                  ║")
            print(
                "║               ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝                  ║")
            print(
                "║               ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║                     ║")
            print(
                "║               ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║                     ║")
            print(
                "║               ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║                     ║")
            print(
                "║               ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝                     ║")
            print(
                "║                                                                              ║")
            print("║                          🏦 金融分析智能体系统                              ║")
            print(
                "║                     Financial Analysis AI Agent System                      ║")
            print(
                "║                                                                              ║")
            print(
                "║    ┌─────────────────────────────────────────────────────────────────┐     ║")
            print("║    │  📊 基本面分析  │  📈 技术分析  │  💰 估值分析  │  📰 新闻分析  │  🤖 智能总结  │    ║")
            print(
                "║    └─────────────────────────────────────────────────────────────────┘     ║")
            print(
                "║                                                                              ║")
            print(
                "╚══════════════════════════════════════════════════════════════════════════════╝")
            print("\n🔹 本系统可以对A股公司进行全面分析，包括：")
            print("  • 基本面分析 - 财务状况、盈利能力和行业地位")
            print("  • 技术面分析 - 价格趋势、交易量和技术指标")
            print("  • 估值分析 - 市盈率、市净率等估值水平")
            print("  • 新闻分析 - 新闻情感分析和风险评估")
            print("\n🔹 支持多种自然语言查询方式：")
            print("  • 分析嘉友国际")
            print("  • 帮我看看比亚迪这只股票怎么样")
            print("  • 我想了解一下腾讯的投资价值")
            print("  • 603871 这个股票值得买吗？")
            print("  • 给我分析一下宁德时代的财务状况")
            print("\n🔹 您可以用任何自然语言描述您的分析需求")
            print("🔹 系统会自动识别股票名称和代码，并进行全面分析")
            print("\n💡 提示：建议使用股票代码（如 000001、600036）以获得更准确的分析结果")
            print("\n" + "─" * 78 + "\n")

            # 获取用户输入
            user_query = input("💬 请输入您的分析需求: ")

            # 确保输入不为空
            while not user_query.strip():
                print(f"{ERROR_ICON} 输入不能为空，请重新输入！")
                user_query = input("请输入您的分析需求: ")

        # 记录用户查询到执行日志
        execution_logger.log_agent_start("main", {"user_query": user_query})

        # ============================================================================
        # 3. AI 辅助结构化信息提取 (AI-Powered Entity Extraction)
        # ============================================================================
        
        print(f"{WAIT_ICON} 正在利用 AI 提取金融实体信息...")
        company_name, stock_code = await extract_entities_from_query(
            user_query,
            debug_printer=lambda message: print(f"{WAIT_ICON} {message}"),
        )

        # 记录提取结果
        logger.info(f"从查询中提取 - 公司名称: {company_name}, 股票代码: {stock_code}")

        if not company_name and not stock_code:
            error_message = "未能从输入中识别出公司名称或股票代码，请提供明确的A股公司名称或6位股票代码。"
            print(f"\n{ERROR_ICON} {error_message}")
            logger.error(error_message)
            finalize_execution_logger(success=False, error=error_message)
            return

        # ============================================================================
        # 4. 执行工作流
        # ============================================================================
        
        # 显示分析开始信息
        print(f"\n{WAIT_ICON} 正在开始对 '{user_query}' 进行金融分析...")
        if company_name:
            print(f"{WAIT_ICON} 分析公司: {company_name}")
        if stock_code:
            print(f"{WAIT_ICON} 股票代码: {stock_code}")
        logger.info(
            f"Starting financial analysis workflow for query: '{user_query}'")

        # 显示分析阶段提示
        print(f"\n{WAIT_ICON} 正在执行基本面分析...")
        print(f"{WAIT_ICON} 正在执行技术面分析...")
        print(f"{WAIT_ICON} 正在执行估值分析...")
        print(f"{WAIT_ICON} 正在执行新闻分析...")
        print(f"{WAIT_ICON} 这可能需要几分钟时间，请耐心等待...\n")

        # 调用共享工作流执行服务
        final_state, session_id = await run_analysis_workflow(
            user_query=user_query,
            execution_dir=execution_logger.execution_dir,
            source="cli",
            session_id=None,
            debug_printer=None,
        )
        print(f"{SUCCESS_ICON} 分析完成！")
        logger.info("Workflow execution completed successfully")

        # ============================================================================
        # 5. 结果处理和报告生成
        # ============================================================================
        
        # 提取并打印最终报告
        if final_state and final_state.data and "final_report" in final_state.data:
            print("\n--- 最终分析报告 (Final Analysis Report) ---\n")
            # print(final_state.data["final_report"])

            # 显示报告文件路径（如果可用）
            if "report_path" in final_state.data:
                print(
                    f"\n{SUCCESS_ICON} 报告已保存到: {final_state.data['report_path']}")
                logger.info(
                    f"Report saved to: {final_state.data['report_path']}")

                # 记录最终报告到执行日志
                execution_logger.log_final_report(
                    final_state.data["final_report"],
                    final_state.data["report_path"]
                )
            logger.info(f"Analysis results persisted to SQLite with session_id={session_id}")
            print(f"{SUCCESS_ICON} 会话结果已写入 SQLite，session_id: {session_id}")
        else:
            print(f"\n{ERROR_ICON} 错误: 无法从工作流中检索最终报告。")
            logger.error(
                "Could not retrieve the final report from the workflow")
            print("调试信息 - 最终状态内容:", final_state)

        # 完成执行日志记录
        finalize_execution_logger(success=True)
        print(f"{SUCCESS_ICON} 执行日志已保存到: {execution_logger.execution_dir}")

    except Exception as e:
        # ============================================================================
        # 8. 错误处理
        # ============================================================================
        
        print(f"\n{ERROR_ICON} 工作流执行期间发生错误: {e}")
        logger.error(f"Error during workflow execution: {e}", exc_info=True)

        # 记录错误并完成执行日志
        finalize_execution_logger(success=False, error=str(e))
        print(f"{ERROR_ICON} 错误日志已保存到: {execution_logger.execution_dir}")


# ============================================================================
# 程序入口点
# ============================================================================

if __name__ == "__main__":
    # 使用asyncio运行主函数
    asyncio.run(main())
