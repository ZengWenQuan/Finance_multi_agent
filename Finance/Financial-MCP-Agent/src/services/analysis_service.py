from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph
from src.persistence.graph_store import GraphStore
from src.persistence.schemas import (
    AgentResultRecord,
    FundamentalStructuredData,
    NewsStructuredData,
    ReportRecord,
    SessionRecord,
    SummaryStructuredData,
    TechnicalStructuredData,
    ValueStructuredData,
)
from src.persistence.sqlite_store import SQLiteSessionStore
from src.services.query_processing import build_initial_state, extract_entities_from_query
from src.services.vector_service import VectorService
from src.utils.state_definition import AgentState


AGENT_CONFIG = {
    "fundamental_agent": {
        "title": "基本面分析",
        "data_key": "fundamental_analysis",
        "error_key": "fundamental_analysis_error",
        "schema_model": FundamentalStructuredData,
    },
    "technical_agent": {
        "title": "技术分析",
        "data_key": "technical_analysis",
        "error_key": "technical_analysis_error",
        "schema_model": TechnicalStructuredData,
    },
    "value_agent": {
        "title": "估值分析",
        "data_key": "value_analysis",
        "error_key": "value_analysis_error",
        "schema_model": ValueStructuredData,
    },
    "news_agent": {
        "title": "新闻分析",
        "data_key": "news_analysis",
        "error_key": "news_analysis_error",
        "schema_model": NewsStructuredData,
    },
    "summary_agent": {
        "title": "综合报告",
        "data_key": "final_report",
        "error_key": "summary_error",
        "schema_model": SummaryStructuredData,
    },
}

STRUCTURED_DATA_KEYS = {
    "fundamental_agent": "fundamental_analysis_structured",
    "technical_agent": "technical_analysis_structured",
    "value_agent": "value_analysis_structured",
    "news_agent": "news_analysis_structured",
    "summary_agent": "summary_analysis_structured",
}


def start_node(state: AgentState) -> AgentState:
    return AgentState.model_validate(state)


def create_workflow_app():
    from src.agents.fundamental_agent import fundamental_agent
    from src.agents.news_agent import news_agent
    from src.agents.summary_agent import summary_agent
    from src.agents.technical_agent import technical_agent
    from src.agents.value_agent import value_agent

    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start_node)
    workflow.add_node("fundamental_analyst", fundamental_agent)
    workflow.add_node("technical_analyst", technical_agent)
    workflow.add_node("value_analyst", value_agent)
    workflow.add_node("news_analyst", news_agent)
    workflow.add_node("summarizer", summary_agent)
    workflow.set_entry_point("start_node")
    workflow.add_edge("start_node", "fundamental_analyst")
    workflow.add_edge("start_node", "technical_analyst")
    workflow.add_edge("start_node", "value_analyst")
    workflow.add_edge("start_node", "news_analyst")
    workflow.add_edge("fundamental_analyst", "summarizer")
    workflow.add_edge("technical_analyst", "summarizer")
    workflow.add_edge("value_analyst", "summarizer")
    workflow.add_edge("news_analyst", "summarizer")
    workflow.add_edge("summarizer", END)
    return workflow.compile()


def get_default_db_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data" / "financial_sessions.db"


def get_default_store() -> SQLiteSessionStore:
    return SQLiteSessionStore(get_default_db_path())


def get_default_vector_store_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data" / "vector_store.json"


def get_default_graph_store_path() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "data" / "graph_store.json"


def get_default_vector_service() -> VectorService:
    return VectorService(get_default_vector_store_path())


def get_default_graph_store() -> GraphStore:
    return GraphStore(get_default_graph_store_path())


def build_session_name(company_name: str | None, stock_code: str | None, user_query: str) -> str:
    if company_name:
        return company_name
    if stock_code:
        return stock_code
    text = (user_query or "").strip()
    return text[:24] if text else f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _build_structured_data(agent_name: str, state: AgentState) -> dict[str, Any]:
    data = state.data
    metadata = state.metadata
    config = AGENT_CONFIG[agent_name]
    content = data.get(config["data_key"], "")
    error = data.get(config["error_key"]) or metadata.get(f"{agent_name}_error")
    exec_time = metadata.get(f"{agent_name}_execution_time")

    common_fields: dict[str, Any] = {
        "company_name": data.get("company_name"),
        "stock_code": data.get("stock_code"),
        "analysis_text": content,
        "execution_time": exec_time,
        "executed": bool(metadata.get(f"{agent_name}_executed")),
        "error": error,
    }

    structured_key = STRUCTURED_DATA_KEYS.get(agent_name)
    raw_structured = data.get(structured_key) if structured_key else None
    if isinstance(raw_structured, dict) and raw_structured:
        merged_structured = dict(raw_structured)
        if content and not merged_structured.get("raw_analysis"):
            merged_structured["raw_analysis"] = content
        merged_structured.setdefault("company_name", common_fields["company_name"])
        merged_structured.setdefault("stock_code", common_fields["stock_code"])
        merged_structured.setdefault("analysis_text", common_fields["analysis_text"])
        merged_structured.setdefault("execution_time", common_fields["execution_time"])
        merged_structured.setdefault("executed", common_fields["executed"])
        merged_structured.setdefault("error", common_fields["error"])
        return merged_structured

    if agent_name == "fundamental_agent":
        return FundamentalStructuredData(
            **common_fields,
            investment_conclusion=_extract_conclusion(content, ["结论", "建议", "综合", "总结"]),
            risk_flags=_extract_risk_flags(content),
        ).model_dump()

    if agent_name == "technical_agent":
        signal = _guess_signal(content)
        trend = _guess_trend(content)
        return TechnicalStructuredData(
            **common_fields,
            trend_analysis=trend,
            short_term_signal=signal,
        ).model_dump()

    if agent_name == "value_agent":
        conclusion = _guess_valuation_conclusion(content)
        return ValueStructuredData(
            **common_fields,
            valuation_conclusion=conclusion,
        ).model_dump()

    if agent_name == "news_agent":
        sentiment = _guess_sentiment(content)
        return NewsStructuredData(
            **common_fields,
            sentiment_summary=sentiment,
            news_based_conclusion=_extract_conclusion(content, ["结论", "总结", "综合"]),
        ).model_dump()

    if agent_name == "summary_agent":
        return SummaryStructuredData(
            company_name=data.get("company_name"),
            stock_code=data.get("stock_code"),
            report_path=data.get("report_path"),
            final_report=data.get("final_report", ""),
            execution_time=metadata.get("summary_agent_execution_time"),
            executed=bool(metadata.get("summary_agent_executed")),
            error=data.get("summary_error") or metadata.get("summary_agent_error"),
        ).model_dump()

    return config["schema_model"](**common_fields).model_dump()


# ---------- 轻量文本特征提取辅助函数 ----------

def _extract_conclusion(text: str, keywords: list[str]) -> str | None:
    """从文本中提取包含关键词的句子作为结论摘要"""
    if not text:
        return None
    for line in text.splitlines():
        for kw in keywords:
            if kw in line:
                stripped = line.strip().lstrip("*#- ")
                if stripped:
                    return stripped[:200]
    return None


def _extract_risk_flags(text: str) -> list[str] | None:
    """提取文本中包含风险词的句子"""
    if not text:
        return None
    risk_words = ["风险", "警告", "注意", "谨慎", "下行", "亏损", "问题", "担忧"]
    flags = []
    for line in text.splitlines():
        if any(w in line for w in risk_words):
            stripped = line.strip().lstrip("*#- ")
            if stripped and len(stripped) > 4:
                flags.append(stripped[:120])
    return flags[:5] if flags else None


def _guess_signal(text: str) -> str | None:
    """从技术分析文本中推断短期信号"""
    if not text:
        return None
    buy_words = ["买入", "看多", "突破", "强势", "上涨", "做多"]
    sell_words = ["卖出", "看空", "跌破", "弱势", "下跌", "做空"]
    hold_words = ["持有", "观望", "震荡", "横盘", "中性"]
    buy_count = sum(text.count(w) for w in buy_words)
    sell_count = sum(text.count(w) for w in sell_words)
    hold_count = sum(text.count(w) for w in hold_words)
    if buy_count > sell_count and buy_count > hold_count:
        return "买入"
    if sell_count > buy_count and sell_count > hold_count:
        return "卖出"
    if hold_count > 0:
        return "观望"
    return None


def _guess_trend(text: str) -> str | None:
    """从技术分析文本中推断趋势方向"""
    if not text:
        return None
    up_words = ["上升趋势", "上行", "趋势向上", "多头", "涨势"]
    down_words = ["下降趋势", "下行", "趋势向下", "空头", "跌势"]
    side_words = ["震荡", "横盘", "盘整", "无明显趋势"]
    if any(w in text for w in up_words):
        return "上升趋势"
    if any(w in text for w in down_words):
        return "下降趋势"
    if any(w in text for w in side_words):
        return "震荡盘整"
    return None


def _guess_valuation_conclusion(text: str) -> str | None:
    """从估值文本中推断高估/低估/合理"""
    if not text:
        return None
    if any(w in text for w in ["低估", "被低估", "价值低估", "估值偏低"]):
        return "低估"
    if any(w in text for w in ["高估", "被高估", "估值偏高", "估值较高"]):
        return "高估"
    if any(w in text for w in ["合理", "估值合理", "估值中性"]):
        return "合理"
    return None


def _guess_sentiment(text: str) -> str | None:
    """从新闻文本中推断情绪"""
    if not text:
        return None
    pos_words = ["利好", "积极", "正面", "上涨", "增长", "强劲", "受益"]
    neg_words = ["利空", "消极", "负面", "下跌", "亏损", "风险", "压力"]
    pos_count = sum(text.count(w) for w in pos_words)
    neg_count = sum(text.count(w) for w in neg_words)
    if pos_count > neg_count * 1.5:
        return "正面"
    if neg_count > pos_count * 1.5:
        return "负面"
    return "中性"


def _build_raw_context(agent_name: str, state: AgentState) -> dict[str, Any]:
    data = state.data
    metadata = state.metadata
    config = AGENT_CONFIG[agent_name]
    related_keys = {
        config["data_key"],
        config["error_key"],
        "query",
        "company_name",
        "stock_code",
        "current_date",
        "current_time_info",
        "report_path",
    }
    return {
        "data": {k: data.get(k) for k in related_keys if k in data},
        "metadata": {
            k: v
            for k, v in metadata.items()
            if k.startswith(agent_name.replace("_agent", ""))
            or k.startswith(agent_name)
            or k in {"summary_agent_execution_time", "summary_agent_error"}
        },
    }


def _build_execution_trace(execution_dir: str | Path, agent_name: str) -> dict[str, Any]:
    execution_path = Path(execution_dir)
    agent_file = execution_path / "agents" / f"{agent_name}_execution.json"
    tool_file = execution_path / "tools" / f"{agent_name}_tools.jsonl"
    return {
        "agent_execution": _load_json(agent_file),
        "tool_calls": _load_jsonl(tool_file),
    }


def persist_analysis_results(
    state: AgentState,
    execution_dir: str | Path,
    user_query: str,
    source: str = "cli",
    store: SQLiteSessionStore | None = None,
    session_id: int | None = None,
    vector_service: VectorService | None = None,
    graph_store: GraphStore | None = None,
) -> int:
    store = store or get_default_store()
    vector_service = vector_service or get_default_vector_service()
    graph_store = graph_store or get_default_graph_store()
    data = state.data
    session_name = build_session_name(data.get("company_name"), data.get("stock_code"), user_query)
    if session_id is None:
        session = SessionRecord(
            session_name=session_name,
            company_name=data.get("company_name"),
            stock_code=data.get("stock_code"),
            user_query=user_query,
            status="completed",
            source=source,
        )
        session_id = store.create_session(session)
    else:
        store.update_session_details(
            session_id=session_id,
            session_name=session_name,
            company_name=data.get("company_name"),
            stock_code=data.get("stock_code"),
            user_query=user_query,
            status="completed",
            source=source,
        )

    for agent_name, config in AGENT_CONFIG.items():
        content = data.get(config["data_key"], "")
        status = "completed" if content else "missing"
        error_message = data.get(config["error_key"])
        if error_message:
            status = "failed"
        record = AgentResultRecord(
            session_id=session_id,
            agent_name=agent_name,
            display_title=config["title"],
            content=content or "",
            structured_data_json=_build_structured_data(agent_name, state),
            execution_trace_json=_build_execution_trace(execution_dir, agent_name),
            raw_context_json=_build_raw_context(agent_name, state),
            status=status,
            error_message=error_message,
        )
        store.upsert_agent_result(record)

    final_report = data.get("final_report")
    if final_report:
        store.upsert_report(
            ReportRecord(
                session_id=session_id,
                final_report=final_report,
                report_path=data.get("report_path"),
                report_markdown_snapshot=final_report,
            )
        )
        vector_service.index_report(
            session_id=session_id,
            stock_code=data.get("stock_code"),
            company_name=data.get("company_name"),
            report_text=final_report,
            metadata={
                "source": source,
                "user_query": user_query,
                "execution_dir": str(execution_dir),
            },
        )
        graph_store.index_report(
            session_id=session_id,
            stock_code=data.get("stock_code"),
            company_name=data.get("company_name"),
            report_text=final_report,
        )

    return session_id


def persist_single_agent_result(
    agent_name: str,
    state: AgentState,
    execution_dir: str | Path,
    session_id: int,
    store: SQLiteSessionStore,
) -> None:
    """持久化单个 Agent 的分析结果"""
    config = AGENT_CONFIG.get(agent_name)
    if not config:
        return

    data = state.data
    content = data.get(config["data_key"], "")
    status = "completed" if content else "missing"
    error_message = data.get(config["error_key"])
    if error_message:
        status = "failed"

    record = AgentResultRecord(
        session_id=session_id,
        agent_name=agent_name,
        display_title=config["title"],
        content=content or "",
        structured_data_json=_build_structured_data(agent_name, state),
        execution_trace_json=_build_execution_trace(execution_dir, agent_name),
        raw_context_json=_build_raw_context(agent_name, state),
        status=status,
        error_message=error_message,
    )
    store.upsert_agent_result(record)


def persist_report_only(
    state: AgentState,
    session_id: int,
    store: SQLiteSessionStore,
    vector_service: VectorService,
    graph_store: GraphStore,
    source: str,
    user_query: str,
    execution_dir: str | Path,
) -> None:
    """仅持久化最终报告和索引"""
    data = state.data
    final_report = data.get("final_report")
    if final_report:
        store.upsert_report(
            ReportRecord(
                session_id=session_id,
                final_report=final_report,
                report_path=data.get("report_path"),
                report_markdown_snapshot=final_report,
            )
        )
        vector_service.index_report(
            session_id=session_id,
            stock_code=data.get("stock_code"),
            company_name=data.get("company_name"),
            report_text=final_report,
            metadata={
                "source": source,
                "user_query": user_query,
                "execution_dir": str(execution_dir),
            },
        )
        graph_store.index_report(
            session_id=session_id,
            stock_code=data.get("stock_code"),
            company_name=data.get("company_name"),
            report_text=final_report,
        )


async def run_analysis_workflow(
    user_query: str,
    execution_dir: str | Path,
    source: str = "cli",
    store: SQLiteSessionStore | None = None,
    session_id: int | None = None,
    debug_printer=None,
    on_node_start=None,  # 新增：节点开始回调
    on_node_end=None,    # 新增：节点结束回调
) -> tuple[AgentState, int]:
    store = store or get_default_store()
    vector_service = get_default_vector_service()
    graph_store = get_default_graph_store()

    company_name, stock_code = await extract_entities_from_query(user_query, debug_printer=debug_printer)
    if not company_name and not stock_code:
        raise ValueError("未能从输入中识别出公司名称或股票代码，请提供明确的A股公司名称或6位股票代码。")

    initial_state = build_initial_state(user_query, company_name, stock_code)
    session_name = build_session_name(company_name, stock_code, user_query)

    if session_id is None:
        session_id = store.create_session(
            SessionRecord(
                session_name=session_name,
                company_name=company_name,
                stock_code=stock_code,
                user_query=user_query,
                status="running",
                source=source,
            )
        )
    else:
        store.update_session_details(
            session_id=session_id,
            session_name=session_name,
            company_name=company_name,
            stock_code=stock_code,
            user_query=user_query,
            status="running",
            source=source,
        )

    app = create_workflow_app()
    final_state = initial_state

    # 映射图节点名称到 Agent 标识符
    node_to_agent = {
        "fundamental_analyst": "fundamental_agent",
        "technical_analyst": "technical_agent",
        "value_analyst": "value_agent",
        "news_analyst": "news_agent",
        "summarizer": "summary_agent",
    }

    # 使用 astream 监听工作流进度
    async for event in app.astream(initial_state, config={"recursion_limit": 30}, stream_mode="updates"):
        for node_name, state_update in event.items():
            agent_name = node_to_agent.get(node_name)
            if not agent_name:
                continue

            # 节点开始（如果需要可以在这里调用 on_node_start）
            # 当前 LangGraph astream updates 模式下，事件是在节点完成后发出的
            # 为了实现"正在分析"，我们可以假设 start_node 之后，四个分析师都开始了
            
            # 更新最终状态
            final_state = AgentState.model_validate({**final_state.model_dump(), **state_update})

            # 持久化单个 Agent 结果
            persist_single_agent_result(agent_name, final_state, execution_dir, session_id, store)
            
            # 回调通知外部（如 backend）
            if on_node_end:
                await on_node_end(agent_name, final_state)

    # 最终持久化报告和索引
    persist_report_only(
        final_state, session_id, store, vector_service, graph_store, source, user_query, execution_dir
    )
    
    # 更新会话状态为已完成
    store.update_session_status(session_id, "completed")
    
    return final_state, session_id
