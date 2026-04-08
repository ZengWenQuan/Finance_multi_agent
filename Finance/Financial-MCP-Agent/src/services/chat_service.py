from __future__ import annotations

import os
import re

from langchain_openai import ChatOpenAI

from src.persistence.schemas import ChatMessageRecord
from src.persistence.sqlite_store import SQLiteSessionStore
from src.persistence.graph_store import GraphStore
from src.services.vector_service import VectorService


def _truncate(text: str, limit: int = 3000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


async def chat_with_session_context(
    store: SQLiteSessionStore,
    session_id: int,
    user_message: str,
    rag_mode: str = "c8_hybrid_rag",
    vector_service: VectorService | None = None,
    graph_store: GraphStore | None = None,
) -> dict:
    session = store.get_session(session_id)
    if not session:
        raise ValueError("Session not found")

    report = store.get_report(session_id)
    agent_results = store.get_agent_results(session_id)
    history = store.get_chat_messages(session_id)
    vector_service = vector_service
    graph_store = graph_store

    store.add_chat_message(
        ChatMessageRecord(session_id=session_id, role="user", content=user_message)
    )

    model_name = os.getenv("OPENAI_COMPATIBLE_MODEL")
    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL")
    if not model_name or not api_key or not base_url:
        reply = "chat_agent 未配置模型环境变量，当前仅完成消息持久化。"
        store.add_chat_message(
            ChatMessageRecord(session_id=session_id, role="assistant", content=reply)
        )
        return {"reply": reply, "mode": "fallback"}

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        max_tokens=1500,
    )

    report_text = report["final_report"] if report else "当前会话还没有最终报告。"
    agent_context_lines = []
    retrieval_context_lines = []

    normalized_mode = _normalize_rag_mode(rag_mode, user_message)
    
    if normalized_mode == "c8_hybrid_rag":
        retrieval_context_lines.extend(
            _build_vector_context(vector_service, user_message, session.get("stock_code"))
        )
        for item in agent_results:
            title = item.get('display_title', '')
            content = item.get('content') or ''
            include_this = False
            
            if "基本面" in title and any(k in user_message for k in ["基本面", "财务", "盈利", "报表", "资产"]):
                include_this = True
            elif ("技术" in title or "Technical" in title) and any(k in user_message for k in ["技术", "K线", "指标", "走势", "均线", "MACD", "阻力", "支撑"]):
                include_this = True
            elif "估值" in title and any(k in user_message for k in ["估值", "市盈率", "PE", "PB", "市净率", "贵", "便宜"]):
                include_this = True
            elif "新闻" in title and any(k in user_message for k in ["新闻", "舆情", "消息", "公告", "事件"]):
                include_this = True
                
            if include_this:
                agent_context_lines.append(f"[{title}]\n{_truncate(content, 1800)}")
        if not agent_context_lines:
            for item in agent_results:
                agent_context_lines.append(
                    f"[{item['display_title']}]\n{_truncate(item.get('content') or '', 1800)}"
                )
    elif normalized_mode == "c9_graph_rag":
        retrieval_context_lines.extend(
            _build_graph_context(
                graph_store,
                user_message,
                session.get("stock_code"),
                session.get("company_name"),
            )
        )
        for item in agent_results:
            agent_context_lines.append(
                f"[{item['display_title']}]\n{_truncate(item.get('content') or '', 1800)}"
            )
    else:
        for item in agent_results:
            agent_context_lines.append(
                f"[{item['display_title']}]\n{_truncate(item.get('content') or '', 1800)}"
            )
    history_lines = []
    for msg in history[-10:]:
        history_lines.append(f"{msg['role']}: {msg['content']}")

    agent_context_str = '\n\n'.join(agent_context_lines) if agent_context_lines else '暂无'
    retrieval_context_str = '\n\n'.join(retrieval_context_lines) if retrieval_context_lines else '暂无'
    history_str = '\n'.join(history_lines) if history_lines else '暂无'

    system_prompt = f"""你是一个面向投研前端页面的聊天助理。

你的职责：
1. 基于当前会话已经完成的分析结果回答问题
2. 优先引用综合报告，其次引用各分 agent 结果
3. 如果上下文中没有答案，明确说明“当前会话结果中没有直接证据”
4. 不要假装重新跑工具，不要编造新的市场数据

当前会话：
- session_name: {session.get('session_name')}
- company_name: {session.get('company_name')}
- stock_code: {session.get('stock_code')}
- user_query: {session.get('user_query')}

最终报告：
{_truncate(report_text, 6000)}

分 agent 结果：
{agent_context_str}

检索增强上下文：
{retrieval_context_str}

历史对话：
{history_str}
"""

    response = await llm.ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    )
    reply = response.content if hasattr(response, "content") else str(response)
    store.add_chat_message(
        ChatMessageRecord(session_id=session_id, role="assistant", content=reply)
    )
    return {"reply": reply, "mode": normalized_mode}


def _normalize_rag_mode(rag_mode: str, user_message: str) -> str:
    supported_modes = {
        "c8_hybrid_rag",
        "c9_graph_rag",
    }
    if rag_mode in supported_modes:
        return rag_mode

    legacy_mapping = {
        "vector_rag": "c8_hybrid_rag",
        "smart_routing": "c8_hybrid_rag",
        "full_context": "c8_hybrid_rag",
        "report_only": "c8_hybrid_rag",
        "graph_rag": "c9_graph_rag",
        "auto_router": "c9_graph_rag",
    }
    if rag_mode in legacy_mapping:
        return legacy_mapping[rag_mode]

    if re.search(r"(对比|比较|同行|产业链|上下游|关联)", user_message):
        return "c9_graph_rag"
    return "c8_hybrid_rag"


def _build_vector_context(
    vector_service: VectorService | None,
    user_message: str,
    stock_code: str | None,
) -> list[str]:
    if vector_service is None:
        return []
    hits = vector_service.similarity_search(user_message, stock_code=stock_code, top_k=4)
    return [
        f"[Vector RAG | {hit.get('company_name') or hit.get('stock_code') or '未知标的'} | {hit.get('title')}]\n"
        f"{_truncate(hit.get('content') or '', 1500)}"
        for hit in hits
    ]


def _build_graph_context(
    graph_store: GraphStore | None,
    user_message: str,
    stock_code: str | None,
    company_name: str | None,
) -> list[str]:
    if graph_store is None:
        return []
    hits = graph_store.query_related(
        user_message,
        stock_code=stock_code,
        company_name=company_name,
        top_k=8,
    )
    return [
        f"[Graph RAG] {item.get('source')} - {item.get('relation')} - {item.get('target')}"
        for item in hits
    ]
