from types import SimpleNamespace

from src.tools.agent_tool_mapping import get_tools_for_agent


def test_get_tools_for_agent_filters_by_whitelist():
    tools = [
        SimpleNamespace(name="get_stock_basic_info"),
        SimpleNamespace(name="crawl_news"),
        SimpleNamespace(name="unknown_tool"),
    ]

    filtered = get_tools_for_agent("news_agent", tools)

    assert [tool.name for tool in filtered] == ["get_stock_basic_info", "crawl_news"]
