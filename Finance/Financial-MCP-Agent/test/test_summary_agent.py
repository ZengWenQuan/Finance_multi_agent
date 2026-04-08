from __future__ import annotations

from src.agents.summary_agent import summary_agent
from test.report_utils import save_agent_report
from src.utils.execution_logger import ExecutionLogger
from src.utils.state_definition import AgentState


class FakeLLM:
    def __init__(self, **_kwargs):
        pass

    async def ainvoke(self, _messages):
        class Response:
            content = "# 比亚迪(sz.002594) 综合分析报告\n\n## 执行摘要\n比亚迪具备长期竞争力。\n\n分析基准时间：2026年04月05日 (2026-04-05) 星期日 12:00:00"

        return Response()


def test_summary_agent_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.summary_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.summary_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={
            "query": "分析比亚迪",
            "company_name": "比亚迪",
            "stock_code": "sz.002594",
            "current_time_info": "2026年04月05日 (2026-04-05) 星期日 12:00:00",
            "current_date": "2026-04-05",
            "fundamental_analysis": "基本面稳健",
            "technical_analysis": "技术面偏强",
            "value_analysis": "估值合理",
            "news_analysis": "新闻面中性偏正面",
        },
        metadata={},
    )

    result = _run_async(summary_agent(state))
    save_agent_report("summary_agent", result.data["final_report"], result.metadata)

    assert "综合分析报告" in result.data["final_report"]
    assert result.metadata["summary_agent_executed"] is True


def test_summary_agent_uses_conservative_fallback_when_inputs_invalid(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agents.summary_agent.ChatOpenAI", FakeLLM)
    monkeypatch.setattr(
        "src.agents.summary_agent.get_execution_logger",
        lambda: ExecutionLogger(base_log_dir=tmp_path / "logs"),
    )

    state = AgentState(
        messages=[],
        data={
            "query": "分析比亚迪",
            "company_name": "比亚迪股票怎么样，",
            "stock_code": "sz.002594",
            "current_time_info": "2026年04月05日 (2026-04-05) 星期日 12:00:00",
            "current_date": "2026-04-05",
            "fundamental_analysis": "基本面分析未获得可用的真实分析结果：系统未登录。",
            "fundamental_analysis_error": "系统未登录",
            "technical_analysis": "Sorry, need more steps to process this request.",
            "technical_analysis_error": "placeholder output",
            "value_analysis": "Sorry, need more steps to process this request.",
            "value_analysis_error": "placeholder output",
            "news_analysis": "",
            "news_analysis_error": "empty output",
        },
        metadata={},
    )

    result = _run_async(summary_agent(state))
    save_agent_report("summary_agent_fallback", result.data["final_report"], result.metadata)

    assert "当前可用真实数据不足" in result.data["final_report"]
    assert "比亚迪股票怎么样" not in result.data["final_report"]


def _run_async(coro):
    import asyncio

    return asyncio.run(coro)
