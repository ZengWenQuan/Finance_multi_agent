from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.agents.news_agent import news_agent
from test.report_utils import save_agent_report
from src.utils.execution_logger import ExecutionLogger
from src.utils.state_definition import AgentState


class FakeReactAgent:
    async def ainvoke(self, *_args, **_kwargs):
        return {"messages": [AIMessage(content="新闻分析结论：比亚迪近期舆情偏正面，但需关注价格战风险。")]}


class FakeLLM:
    def __init__(self, **_kwargs):
        pass


def test_news_agent_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.news_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.news_agent.get_mcp_tools",
        lambda: _async_result([SimpleNamespace(name="crawl_news")]),
    )
    monkeypatch.setattr("src.agents.news_agent.create_react_agent", lambda *_args, **_kwargs: FakeReactAgent())
    monkeypatch.setattr(
        "src.agents.news_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={"query": "分析比亚迪新闻面", "company_name": "比亚迪", "stock_code": "sz.002594"},
        metadata={},
    )

    result = _run_async(news_agent(state))
    save_agent_report("news_agent", result.data["news_analysis"], result.metadata)

    assert "比亚迪" in result.data["news_analysis"]
    assert result.metadata["news_agent_executed"] is True


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)


async def _async_result(value):
    return value
