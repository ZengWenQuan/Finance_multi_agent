"""
NewsAnalysis Agent: Performs news analysis with sentiment and risk assessment using ReAct Agent framework.
新闻分析 Agent：使用ReAct Agent框架进行新闻分析，包含情感分析和风险评估
"""
import sys
import os
from pathlib import Path

# 将项目根目录添加到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import json
from typing import Dict, Any, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langgraph.prebuilt import create_react_agent
import time

from src.utils.state_definition import AgentState
from src.tools.mcp_client import get_mcp_tools
from src.tools.agent_tool_mapping import get_tools_for_agent
from src.utils.analysis_quality import (
    build_agent_failure_message,
    extract_analysis_text,
    sanitize_company_name,
    validate_analysis_output,
)
from src.schemas.agent_outputs import NewsAnalysisOutput
from src.utils.logging_config import setup_logger, ERROR_ICON, SUCCESS_ICON, WAIT_ICON
from src.utils.execution_logger import get_execution_logger
from src.utils.structured_output import build_structured_output
from dotenv import load_dotenv

# 从.env文件加载环境变量
load_dotenv(override=True)

logger = setup_logger(__name__)
DEFAULT_AGENT_MAX_TOKENS = int(
    os.getenv("AGENT_MAX_TOKENS", os.getenv("OPENAI_COMPATIBLE_MAX_TOKENS", "6000"))
)
DEFAULT_AGENT_RECURSION_LIMIT = int(os.getenv("AGENT_RECURSION_LIMIT", "25"))


async def news_agent(state: AgentState) -> AgentState:
    """
    使用ReAct框架进行新闻分析，包含情感分析和风险评估，直接集成MCP工具
    
    Args:
        state: 包含用户查询的当前 Agent状态

    Returns:
        更新后的AgentState，包含新闻分析结果
    """
    logger.info(
        f"{WAIT_ICON} NewsAgent: Starting news analysis using ReAct framework.")
    state = AgentState.model_validate(state)

    # 获取执行日志记录器，用于记录 Agent的执行过程
    execution_logger = get_execution_logger()
    agent_name = "news_agent"

    # 从状态中提取当前数据、消息和元数据
    current_data = state.data
    current_messages = state.messages
    current_metadata = state.metadata
    user_query = current_data.get("query")

    # 记录 Agent开始执行，包含关键信息
    execution_logger.log_agent_start(agent_name, {
        "user_query": user_query,
        "stock_code": current_data.get("stock_code"),
        "company_name": current_data.get("company_name"),
        "input_data_keys": list(current_data.keys())
    })

    # 验证用户查询是否存在
    if not user_query:
        logger.error(
            f"{ERROR_ICON} NewsAgent: User query is missing in state data.")
        current_data["news_analysis_error"] = "User query is missing."

        # 记录 Agent执行失败
        execution_logger.log_agent_complete(
            agent_name, current_data, 0, False, "User query is missing")

        return AgentState(data=current_data, messages=current_messages, metadata=current_metadata)

    # 记录 Agent开始时间，用于计算执行时长
    agent_start_time = time.time()

    try:
        # 使用API调用
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        model_name = os.getenv("OPENAI_COMPATIBLE_MODEL")

        # 验证必要的环境变量是否存在
        if not all([api_key, base_url, model_name]):
            logger.error(f"{ERROR_ICON} NewsAgent: Missing OpenAI environment variables.")
            current_data["news_analysis_error"] = "Missing OpenAI environment variables."
            execution_logger.log_agent_complete(agent_name, current_data, time.time() - agent_start_time, False, "Missing OpenAI environment variables")
            return AgentState(data=current_data, messages=current_messages, metadata=current_metadata)

        logger.info(f"{WAIT_ICON} NewsAgent: Creating ChatOpenAI with model {model_name}")
        # 创建LLM实例，设置合适的参数
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,  # 较低的温度确保分析的一致性
            max_tokens=DEFAULT_AGENT_MAX_TOKENS
        )

        # 2. 获取MCP工具集
        logger.info(f"{WAIT_ICON} NewsAgent: Fetching MCP tools...")
        try:
            all_mcp_tools = await get_mcp_tools()
            mcp_tools = get_tools_for_agent(agent_name, all_mcp_tools)
            if not mcp_tools:
                logger.error(
                    f"{ERROR_ICON} NewsAgent: No MCP tools available after filtering.")
                current_data["news_analysis_error"] = "No MCP tools available after filtering."
                current_data["news_analysis"] = f"新闻分析失败: 无法加载 MCP 工具集集。这通常是由于 MCP 服务器 (`mcp_server.py`) 启动异常或语法错误导致的。请检查服务端日志。"

                # 记录 Agent执行失败
                execution_logger.log_agent_complete(agent_name, current_data, time.time(
                ) - agent_start_time, False, "No MCP tools available")

                return AgentState(data=current_data, messages=current_messages, metadata=current_metadata)

            logger.info(
                f"{SUCCESS_ICON} NewsAgent: Successfully loaded {len(mcp_tools)} tools.")

            # 打印可用工具列表，便于调试
            tool_names = [tool.name for tool in mcp_tools]
            logger.info(f"Available tools: {tool_names}")

            # 3. 创建ReAct Agent - 只传入LLM和工具
            logger.info(
                f"{WAIT_ICON} NewsAgent: Creating ReAct agent...")
            agent = create_react_agent(llm, mcp_tools)

            # 4. 准备输入数据，构建详细的新闻分析请求
            stock_code = current_data.get('stock_code', 'Unknown')
            company_name = sanitize_company_name(current_data.get('company_name')) or 'Unknown'
            current_time_info = current_data.get('current_time_info', '未知时间')
            current_date = current_data.get('current_date', '未知日期')

            # 构建精简的新闻分析请求
            agent_input = f"""请对{company_name}做简要新闻分析。

股票代码：{stock_code}（调用工具时请务必原样传入此代码，不要修改前缀）
当前日期：{current_date}

请调用以下工具（只调一次）：
1. crawl_news(query="{company_name}") - 爬取公司相关新闻

拿到新闻后，列出3-5条关键新闻标题和摘要，然后总结整体市场情绪（正面/负面/中性），用2-3句话概括即可。

回答请控制在300字以内，不要重复相同内容。

输出格式要求：
## 新闻摘要
## 市场情绪

不要编造新闻内容。不要重复。"""

            logger.info(f"Agent input: {agent_input}")

            # 5. 调用ReAct Agent - 使用正确的messages格式
            logger.info(
                f"{WAIT_ICON} NewsAgent: Calling ReAct agent...")
            start_time = time.time()

            # LangGraph ReAct Agent需要messages格式的输入
            input_data = {
                "messages": [HumanMessage(content=agent_input)]
            }

            # 调用 Agent执行分析
            response = await agent.ainvoke(input_data, config={"recursion_limit": DEFAULT_AGENT_RECURSION_LIMIT})

            end_time = time.time()
            execution_time = end_time - start_time

            logger.info(
                f"ReAct agent execution completed in {execution_time:.2f} seconds")

            # 6. 提取分析结果
            final_output = extract_analysis_text(response)
            analysis_check = validate_analysis_output(final_output)
            if not analysis_check.is_valid:
                issue = analysis_check.issue or "analysis output is invalid"
                logger.error(f"{ERROR_ICON} NewsAgent: {issue}")
                current_data["news_analysis_error"] = issue
                final_output = build_agent_failure_message("新闻分析", issue, final_output)

            logger.info(
                f"Final extracted analysis length: {len(final_output)} characters")
            print(f"NEWSAGENT: {final_output}")
            # 7. 记录LLM交互，用于后续分析和优化
            model_config = {
                "model": model_name,
                "temperature": 0.3,
                "max_tokens": DEFAULT_AGENT_MAX_TOKENS,
                "api_base": base_url
            }
            
            execution_logger.log_llm_interaction(
                agent_name=agent_name,
                interaction_type="react_agent",
                input_messages=[{"role": "user", "content": agent_input}],
                output_content=final_output,
                model_config=model_config,
                execution_time=execution_time
            )

            logger.info(
                f"{SUCCESS_ICON} NewsAgent: Successfully completed news analysis.")

            structured_output = await build_structured_output(
                llm=llm,
                schema_cls=NewsAnalysisOutput,
                agent_label="新闻分析",
                company_name=company_name,
                stock_code=stock_code,
                raw_analysis=final_output,
                issue=current_data.get("news_analysis_error"),
            )

            # 8. 更新状态，保存分析结果和元数据
            current_data["news_analysis"] = final_output
            current_data["news_analysis_structured"] = structured_output.model_dump()
            current_metadata["news_agent_executed"] = analysis_check.is_valid
            current_metadata["news_agent_timestamp"] = str(time.time())
            current_metadata["news_agent_execution_time"] = f"{execution_time:.2f} seconds"

            # 9. 添加消息记录，保持对话历史
            new_message = AIMessage(content="新闻分析已完成")
            updated_messages = list(current_messages) + [new_message]

            # 记录 Agent执行成功
            total_execution_time = time.time() - agent_start_time
            execution_logger.log_agent_complete(agent_name, {
                "news_analysis_length": len(final_output),
                "analysis_preview": final_output[:500] if len(final_output) > 500 else final_output,
                "llm_execution_time": execution_time,
                "total_execution_time": total_execution_time
            }, total_execution_time, analysis_check.is_valid, current_data.get("news_analysis_error"))

            return AgentState(
                data=current_data,
                messages=updated_messages,
                metadata=current_metadata
            )

        except Exception as e:
            logger.error(
                f"{ERROR_ICON} NewsAgent: Error in MCP or agent execution: {e}", exc_info=True)
            current_data[
                "news_analysis_error"] = f"Error in MCP or agent execution: {e}"
            current_data["news_analysis"] = f"新闻分析过程中出现错误: {str(e)}"
            current_data["news_analysis_structured"] = NewsAnalysisOutput(
                company_name=sanitize_company_name(current_data.get("company_name")),
                stock_code=current_data.get("stock_code"),
                summary=None,
                missing_data=[str(e)],
                raw_analysis=current_data["news_analysis"],
            ).model_dump()
            current_metadata["news_agent_error"] = str(e)

            # 记录 Agent执行失败
            execution_logger.log_agent_complete(
                agent_name, current_data, time.time() - agent_start_time, False, str(e))

            return AgentState(
                data=current_data,
                messages=current_messages,
                metadata=current_metadata
            )

    except Exception as e:
        logger.error(
            f"{ERROR_ICON} NewsAgent: Error during execution: {e}", exc_info=True)
        current_data["news_analysis_error"] = f"Error during execution: {e}"
        current_data["news_analysis_structured"] = NewsAnalysisOutput(
            company_name=sanitize_company_name(current_data.get("company_name")),
            stock_code=current_data.get("stock_code"),
            summary=None,
            missing_data=[str(e)],
            raw_analysis=current_data.get("news_analysis", ""),
        ).model_dump()
        current_metadata["news_agent_error"] = str(e)

        # 记录 Agent执行失败
        execution_logger.log_agent_complete(
            agent_name, current_data, time.time() - agent_start_time, False, str(e))

        return AgentState(
            data=current_data,
            messages=current_messages,
            metadata=current_metadata
        )


# 本地测试函数
async def test_news_agent():
    """新闻分析 Agent的测试函数"""
    from src.utils.state_definition import AgentState
    from datetime import datetime

    # 准备测试数据，包含当前时间信息
    current_datetime = datetime.now()
    current_date_cn = current_datetime.strftime("%Y年%m月%d日")
    current_date_en = current_datetime.strftime("%Y-%m-%d")
    current_weekday_cn = ["星期一", "星期二", "星期三", "星期四",
                          "星期五", "星期六", "星期日"][current_datetime.weekday()]
    current_time = current_datetime.strftime("%H:%M:%S")
    current_time_info = f"{current_date_cn} ({current_date_en}) {current_weekday_cn} {current_time}"

    # 创建测试状态，模拟真实的用户查询
    test_state = AgentState(
        messages=[],
        data={
            "query": "分析嘉友国际的新闻情况",
            "stock_code": "sh.603871",
            "company_name": "嘉友国际",
            "current_date": current_date_en,
            "current_date_cn": current_date_cn,
            "current_time": current_time,
            "current_weekday_cn": current_weekday_cn,
            "current_time_info": current_time_info,
            "analysis_timestamp": current_datetime.isoformat()
        },
        metadata={}
    )

    # 运行 Agent并输出结果
    result = await news_agent(test_state)
    print("News Analysis Result:")
    print(result.data.get("news_analysis", "No analysis found"))

    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_news_agent())
