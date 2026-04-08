from __future__ import annotations

import asyncio

from src.services.analysis_service import persist_analysis_results
from src.utils.state_definition import AgentState


def test_persist_analysis_results_indexes_rag_stores(tmp_path):
    from src.persistence.graph_store import GraphStore
    from src.persistence.sqlite_store import SQLiteSessionStore
    from src.services.vector_service import VectorService

    store = SQLiteSessionStore(tmp_path / "sessions.db")
    vector_service = VectorService(tmp_path / "vector.json")
    graph_store = GraphStore(tmp_path / "graph.json")

    state = AgentState(
        messages=[],
        data={
            "company_name": "比亚迪",
            "stock_code": "sz.002594",
            "fundamental_analysis": "基本面稳健",
            "technical_analysis": "技术面偏强",
            "value_analysis": "估值合理",
            "news_analysis": "新闻面正面",
            "final_report": "# 比亚迪综合分析\n比亚迪毛利率改善，风险来自价格战。",
        },
        metadata={
            "fundamental_agent_executed": True,
            "technical_agent_executed": True,
            "value_agent_executed": True,
            "news_agent_executed": True,
            "summary_agent_executed": True,
        },
    )

    session_id = persist_analysis_results(
        state=state,
        execution_dir=tmp_path / "logs",
        user_query="分析比亚迪",
        store=store,
        vector_service=vector_service,
        graph_store=graph_store,
    )

    assert session_id > 0
    assert vector_service.similarity_search("比亚迪毛利率", stock_code="sz.002594")
    assert graph_store.query_related("比亚迪风险", stock_code="sz.002594", company_name="比亚迪")
