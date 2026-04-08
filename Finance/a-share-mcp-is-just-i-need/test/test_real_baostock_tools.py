from __future__ import annotations

import os
import pytest

from src.baostock_data_source import BaostockDataSource
from src.tools.analysis import register_analysis_tools
from src.tools.date_utils import register_date_utils_tools
from src.tools.financial_reports import register_financial_report_tools
from src.tools.indices import register_index_tools
from src.tools.macroeconomic import register_macroeconomic_tools
from src.tools.market_overview import register_market_overview_tools
from src.tools.stock_market import register_stock_market_tools


BYD_CODE = "sz.002594"


class FakeFastMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def build_real_registry():
    app = FakeFastMCP()
    data_source = BaostockDataSource()
    register_stock_market_tools(app, data_source)
    register_financial_report_tools(app, data_source)
    register_index_tools(app, data_source)
    register_market_overview_tools(app, data_source)
    register_macroeconomic_tools(app, data_source)
    register_date_utils_tools(app, data_source)
    register_analysis_tools(app, data_source)
    return app.tools


REAL_TOOL_CASES = [
    ("get_historical_k_data", {"code": BYD_CODE, "start_date": "2024-01-01", "end_date": "2024-03-31"}),
    ("get_stock_basic_info", {"code": BYD_CODE}),
    ("get_dividend_data", {"code": BYD_CODE, "year": "2023"}),
    ("get_adjust_factor_data", {"code": BYD_CODE, "start_date": "2024-01-01", "end_date": "2024-03-31"}),
    ("get_profit_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_operation_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_growth_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_balance_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_cash_flow_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_dupont_data", {"code": BYD_CODE, "year": "2024", "quarter": 4}),
    ("get_performance_express_report", {"code": BYD_CODE, "start_date": "2024-01-01", "end_date": "2024-12-31"}),
    ("get_forecast_report", {"code": BYD_CODE, "start_date": "2024-01-01", "end_date": "2024-12-31"}),
    ("get_stock_industry", {"code": BYD_CODE}),
    ("get_sz50_stocks", {"date": "2024-06-28"}),
    ("get_hs300_stocks", {"date": "2024-06-28"}),
    ("get_zz500_stocks", {"date": "2024-06-28"}),
    ("get_trade_dates", {"start_date": "2024-01-01", "end_date": "2024-01-31"}),
    ("get_all_stock", {"date": "2024-06-28"}),
    ("get_deposit_rate_data", {"start_date": "2015-01-01", "end_date": "2015-12-31"}),
    ("get_loan_rate_data", {"start_date": "2015-01-01", "end_date": "2015-12-31"}),
    ("get_required_reserve_ratio_data", {"start_date": "2015-01-01", "end_date": "2015-12-31"}),
    ("get_money_supply_data_month", {"start_date": "2024-01", "end_date": "2024-03"}),
    ("get_money_supply_data_year", {"start_date": "2023", "end_date": "2024"}),
]

ALLOW_NO_DATA_TOOLS = {
    "get_adjust_factor_data",
    "get_performance_express_report",
}


@pytest.mark.parametrize(("tool_name", "kwargs"), REAL_TOOL_CASES)
def test_real_baostock_tool_returns_data(tool_name: str, kwargs: dict):
    tools = build_real_registry()
    result = tools[tool_name](**kwargs)

    # 保存结果到报告文件夹
    report_dir = os.path.join(os.path.dirname(__file__), "report")
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, f"{tool_name}.md"), "w", encoding="utf-8") as f:
        f.write(result)

    assert isinstance(result, str)
    assert result
    if tool_name in ALLOW_NO_DATA_TOOLS and result.startswith("Error:"):
        assert "No " in result
    else:
        assert not result.startswith("Error:")
        assert "No data available" not in result


def test_real_latest_trading_date_and_timeframe():
    tools = build_real_registry()

    latest = tools["get_latest_trading_date"]()
    timeframe = tools["get_market_analysis_timeframe"]("recent")

    # 保存结果
    report_dir = os.path.join(os.path.dirname(__file__), "report")
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "latest_trading_date.md"), "w", encoding="utf-8") as f:
        f.write(latest)
    with open(os.path.join(report_dir, "market_analysis_timeframe.md"), "w", encoding="utf-8") as f:
        f.write(timeframe)

    assert isinstance(latest, str)
    assert len(latest) == 10
    assert latest.count("-") == 2
    assert "ISO日期范围:" in timeframe


def test_real_stock_analysis_for_byd():
    tools = build_real_registry()
    result = tools["get_stock_analysis"](BYD_CODE, analysis_type="fundamental")

    # 保存结果
    report_dir = os.path.join(os.path.dirname(__file__), "report")
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "stock_analysis_byd.md"), "w", encoding="utf-8") as f:
        f.write(result)

    assert isinstance(result, str)
    assert result
    assert "分析生成失败" not in result
    assert "数据分析报告" in result
