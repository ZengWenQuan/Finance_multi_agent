from __future__ import annotations

import asyncio

from src.persistence.graph_store import GraphStore
from src.persistence.schemas import AgentResultRecord, ChatMessageRecord, ReportRecord, SessionRecord
from src.persistence.sqlite_store import SQLiteSessionStore
from src.services.chat_service import chat_with_session_context
from src.services.vector_service import VectorService


class FakeLLM:
    async def ainvoke(self, messages):
        class Response:
            content = "基于检索上下文生成的回答"

        return Response()


def test_vector_service_indexes_and_searches(tmp_path):
    service = VectorService(tmp_path / "vector.json")
    service.index_report(
        session_id=1,
        stock_code="sz.002594",
        company_name="比亚迪",
        report_text="# 基本面分析\n比亚迪毛利率持续改善。\n# 风险因素\n原材料价格波动带来压力。",
    )

    hits = service.similarity_search("比亚迪毛利率怎么样", stock_code="sz.002594", top_k=2)

    assert hits
    assert hits[0]["company_name"] == "比亚迪"


def test_graph_store_indexes_and_queries(tmp_path):
    store = GraphStore(tmp_path / "graph.json")
    count = store.index_report(
        session_id=1,
        stock_code="sz.002594",
        company_name="比亚迪",
        report_text="行业竞争激烈。\n风险因素：原材料价格波动。\nPE 估值处于历史中枢。",
    )

    hits = store.query_related("比亚迪有哪些风险", stock_code="sz.002594", company_name="比亚迪")

    assert count > 0
    assert any(item["relation"] == "风险提示" for item in hits)


def test_chat_service_supports_c8_and_c9_modes(tmp_path, monkeypatch):
    sqlite_store = SQLiteSessionStore(tmp_path / "sessions.db")
    session_id = sqlite_store.create_session(
        SessionRecord(
            session_name="比亚迪",
            company_name="比亚迪",
            stock_code="sz.002594",
            user_query="分析比亚迪",
        )
    )
    sqlite_store.upsert_report(
        ReportRecord(
            session_id=session_id,
            final_report="# 综合报告\n比亚迪毛利率改善，估值中性。",
            report_markdown_snapshot="# 综合报告\n比亚迪毛利率改善，估值中性。",
        )
    )
    sqlite_store.upsert_agent_result(
        AgentResultRecord(
            session_id=session_id,
            agent_name="fundamental_agent",
            display_title="基本面分析",
            content="比亚迪盈利能力改善。",
        )
    )
    sqlite_store.add_chat_message(ChatMessageRecord(session_id=session_id, role="user", content="先前问题"))

    vector_service = VectorService(tmp_path / "vector.json")
    vector_service.index_report(
        session_id=session_id,
        stock_code="sz.002594",
        company_name="比亚迪",
        report_text="# 基本面分析\n比亚迪毛利率改善。",
    )
    graph_store = GraphStore(tmp_path / "graph.json")
    graph_store.index_report(
        session_id=session_id,
        stock_code="sz.002594",
        company_name="比亚迪",
        report_text="风险因素：原材料价格波动。",
    )

    monkeypatch.setattr("src.services.chat_service.ChatOpenAI", lambda **_: FakeLLM())

    c8_result = asyncio.run(
        chat_with_session_context(
            sqlite_store,
            session_id,
            "比亚迪毛利率怎么样",
            "c8_hybrid_rag",
            vector_service=vector_service,
            graph_store=graph_store,
        )
    )
    c9_result = asyncio.run(
        chat_with_session_context(
            sqlite_store,
            session_id,
            "比亚迪有哪些风险",
            "c9_graph_rag",
            vector_service=vector_service,
            graph_store=graph_store,
        )
    )

    assert c8_result["mode"] == "c8_hybrid_rag"
    assert c9_result["mode"] == "c9_graph_rag"
