from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.agents.technical_agent import technical_agent
from test.report_utils import save_agent_report
from src.utils.execution_logger import ExecutionLogger
from src.utils.state_definition import AgentState


class FakeReactAgent:
    async def ainvoke(self, *_args, **_kwargs):
        return {"messages": [AIMessage(content="技术分析结论：比亚迪短期偏强，MACD 金叉。")]}


class FakeLLM:
    def __init__(self, **_kwargs):
        pass


def test_technical_agent_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.technical_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.technical_agent.get_mcp_tools",
        lambda: _async_result([SimpleNamespace(name="get_historical_k_data")]),
    )
    monkeypatch.setattr("src.agents.technical_agent.create_react_agent", lambda *_args, **_kwargs: FakeReactAgent())
    monkeypatch.setattr(
        "src.agents.technical_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={"query": "分析比亚迪技术面", "company_name": "比亚迪", "stock_code": "sz.002594"},
        metadata={},
    )

    result = _run_async(technical_agent(state))
    save_agent_report("technical_agent", result.data["technical_analysis"], result.metadata)

    assert "MACD" in result.data["technical_analysis"]
    assert result.metadata["technical_agent_executed"] is True


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)


async def _async_result(value):
    return value
