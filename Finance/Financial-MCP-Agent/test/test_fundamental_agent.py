from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage

from src.agents.fundamental_agent import fundamental_agent
from test.report_utils import save_agent_report
from src.utils.execution_logger import ExecutionLogger
from src.utils.state_definition import AgentState


class FakeReactAgent:
    async def ainvoke(self, *_args, **_kwargs):
        return {"messages": [AIMessage(content="基本面分析结论：比亚迪盈利能力稳健。")]}


class FakeLLM:
    def __init__(self, **_kwargs):
        pass


def test_fundamental_agent_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.fundamental_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.fundamental_agent.get_mcp_tools",
        lambda: _async_result([SimpleNamespace(name="get_stock_basic_info")]),
    )
    monkeypatch.setattr("src.agents.fundamental_agent.create_react_agent", lambda *_args, **_kwargs: FakeReactAgent())
    monkeypatch.setattr(
        "src.agents.fundamental_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={"query": "分析比亚迪基本面", "company_name": "比亚迪", "stock_code": "sz.002594"},
        metadata={},
    )

    result = _run_async(fundamental_agent(state))
    save_agent_report("fundamental_agent", result.data["fundamental_analysis"], result.metadata)

    assert "比亚迪" in result.data["fundamental_analysis"]
    assert result.metadata["fundamental_agent_executed"] is True


def test_fundamental_agent_marks_placeholder_as_failure(monkeypatch, tmp_path):
    class PlaceholderReactAgent:
        async def ainvoke(self, *_args, **_kwargs):
            return {"messages": [AIMessage(content="Sorry, need more steps to process this request.")]}

    monkeypatch.setattr("src.agents.fundamental_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.fundamental_agent.get_mcp_tools",
        lambda: _async_result([SimpleNamespace(name="get_stock_basic_info")]),
    )
    monkeypatch.setattr("src.agents.fundamental_agent.create_react_agent", lambda *_args, **_kwargs: PlaceholderReactAgent())
    monkeypatch.setattr(
        "src.agents.fundamental_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={"query": "分析比亚迪基本面", "company_name": "比亚迪", "stock_code": "sz.002594"},
        metadata={},
    )

    result = _run_async(fundamental_agent(state))
    save_agent_report("fundamental_agent_invalid", result.data["fundamental_analysis"], result.metadata)

    assert result.metadata["fundamental_agent_executed"] is False
    assert "未获得可用的真实分析结果" in result.data["fundamental_analysis"]


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)


async def _async_result(value):
    return value
