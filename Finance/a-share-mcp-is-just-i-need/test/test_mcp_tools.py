from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.tools.analysis import register_analysis_tools
from src.tools.date_utils import register_date_utils_tools
from src.tools.financial_reports import register_financial_report_tools
from src.tools.indices import register_index_tools
from src.tools.macroeconomic import register_macroeconomic_tools
from src.tools.market_overview import register_market_overview_tools
from src.tools.news_crawler import register_news_crawler_tools
from src.tools.stock_market import register_stock_market_tools


EXPECTED_TOOL_NAMES = {
    "get_historical_k_data",
    "get_stock_basic_info",
    "get_dividend_data",
    "get_adjust_factor_data",
    "get_profit_data",
    "get_operation_data",
    "get_growth_data",
    "get_balance_data",
    "get_cash_flow_data",
    "get_dupont_data",
    "get_performance_express_report",
    "get_forecast_report",
    "get_stock_industry",
    "get_sz50_stocks",
    "get_hs300_stocks",
    "get_zz500_stocks",
    "get_trade_dates",
    "get_all_stock",
    "get_deposit_rate_data",
    "get_loan_rate_data",
    "get_required_reserve_ratio_data",
    "get_money_supply_data_month",
    "get_money_supply_data_year",
    "get_latest_trading_date",
    "get_market_analysis_timeframe",
    "get_stock_analysis",
    "crawl_news",
}


class FakeFastMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@dataclass
class FakeDataSource:
    calls: list[tuple[str, dict]] = field(default_factory=list)

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))

    def get_historical_k_data(self, **kwargs):
        self._record("get_historical_k_data", **kwargs)
        return pd.DataFrame(
            [
                {"date": "2024-01-02", "close": 10.0, "volume": 1000},
                {"date": "2024-06-28", "close": 12.0, "volume": 1500},
            ]
        )

    def get_stock_basic_info(self, **kwargs):
        self._record("get_stock_basic_info", **kwargs)
        return pd.DataFrame(
            [
                {
                    "code": kwargs["code"],
                    "code_name": "平安银行",
                    "industry": "银行",
                    "ipoDate": "1991-04-03",
                }
            ]
        )

    def get_dividend_data(self, **kwargs):
        self._record("get_dividend_data", **kwargs)
        return pd.DataFrame([{"year": kwargs["year"], "dividCashPsBeforeTax": 0.5}])

    def get_adjust_factor_data(self, **kwargs):
        self._record("get_adjust_factor_data", **kwargs)
        return pd.DataFrame([{"dividOperateDate": "2024-06-28", "foreAdjustFactor": 1.2}])

    def get_profit_data(self, **kwargs):
        self._record("get_profit_data", **kwargs)
        return pd.DataFrame([{"roeAvg": 12.3, "npMargin": 8.8, "epsTTM": 1.1}])

    def get_operation_data(self, **kwargs):
        self._record("get_operation_data", **kwargs)
        return pd.DataFrame([{"NRTurnRatio": 3.2, "INVTurnRatio": 4.5}])

    def get_growth_data(self, **kwargs):
        self._record("get_growth_data", **kwargs)
        return pd.DataFrame([{"YOYEquity": 7.5, "YOYAsset": 9.1, "YOYNI": 12.4}])

    def get_balance_data(self, **kwargs):
        self._record("get_balance_data", **kwargs)
        return pd.DataFrame([{"currentRatio": 1.6, "assetLiabRatio": 55.2}])

    def get_cash_flow_data(self, **kwargs):
        self._record("get_cash_flow_data", **kwargs)
        return pd.DataFrame([{"CAToAsset": 0.21, "NCFOToOR": 0.18}])

    def get_dupont_data(self, **kwargs):
        self._record("get_dupont_data", **kwargs)
        return pd.DataFrame([{"dupontROE": 12.3, "dupontAssetStoEquity": 2.1}])

    def get_performance_express_report(self, **kwargs):
        self._record("get_performance_express_report", **kwargs)
        return pd.DataFrame([{"performanceExpPubDate": "2024-07-01", "performanceExpressROEWa": 11.2}])

    def get_forecast_report(self, **kwargs):
        self._record("get_forecast_report", **kwargs)
        return pd.DataFrame([{"profitForcastExpPubDate": "2024-07-05", "profitForcastType": "预增"}])

    def get_stock_industry(self, **kwargs):
        self._record("get_stock_industry", **kwargs)
        return pd.DataFrame(
            [
                {"code": "sz.000001", "industry": "银行"},
                {"code": "sh.600036", "industry": "银行"},
            ]
        )

    def get_sz50_stocks(self, **kwargs):
        self._record("get_sz50_stocks", **kwargs)
        return pd.DataFrame([{"code": "sh.600000", "code_name": "浦发银行"}])

    def get_hs300_stocks(self, **kwargs):
        self._record("get_hs300_stocks", **kwargs)
        return pd.DataFrame([{"code": "sh.600519", "code_name": "贵州茅台"}])

    def get_zz500_stocks(self, **kwargs):
        self._record("get_zz500_stocks", **kwargs)
        return pd.DataFrame([{"code": "sz.002594", "code_name": "比亚迪"}])

    def get_trade_dates(self, **kwargs):
        self._record("get_trade_dates", **kwargs)
        return pd.DataFrame(
            [
                {"calendar_date": "2024-06-27", "is_trading_day": "1"},
                {"calendar_date": "2024-06-28", "is_trading_day": "1"},
                {"calendar_date": "2099-06-29", "is_trading_day": "1"},
            ]
        )

    def get_all_stock(self, **kwargs):
        self._record("get_all_stock", **kwargs)
        return pd.DataFrame([{"code": "sz.000001", "code_name": "平安银行", "tradeStatus": "1"}])

    def get_deposit_rate_data(self, **kwargs):
        self._record("get_deposit_rate_data", **kwargs)
        return pd.DataFrame([{"pubDate": "2024-01-01", "demandDepositRate": 0.2}])

    def get_loan_rate_data(self, **kwargs):
        self._record("get_loan_rate_data", **kwargs)
        return pd.DataFrame([{"pubDate": "2024-01-01", "loanRate1Year": 3.45}])

    def get_required_reserve_ratio_data(self, **kwargs):
        self._record("get_required_reserve_ratio_data", **kwargs)
        return pd.DataFrame([{"effectiveDate": "2024-02-05", "bigBankRrr": 10.0}])

    def get_money_supply_data_month(self, **kwargs):
        self._record("get_money_supply_data_month", **kwargs)
        return pd.DataFrame([{"statYear": "2024-06", "m2": 301.0}])

    def get_money_supply_data_year(self, **kwargs):
        self._record("get_money_supply_data_year", **kwargs)
        return pd.DataFrame([{"statYear": "2024", "m2": 300.0}])

    def crawl_news(self, query: str, top_k: int = 10):
        self._record("crawl_news", query=query, top_k=top_k)
        return f"新闻结果: {query} ({top_k})"


def build_registry():
    app = FakeFastMCP()
    data_source = FakeDataSource()
    register_stock_market_tools(app, data_source)
    register_financial_report_tools(app, data_source)
    register_index_tools(app, data_source)
    register_market_overview_tools(app, data_source)
    register_macroeconomic_tools(app, data_source)
    register_date_utils_tools(app, data_source)
    register_analysis_tools(app, data_source)
    register_news_crawler_tools(app, data_source)
    return app.tools, data_source


def assert_markdown_table(result: str) -> None:
    assert "|" in result
    assert "---" in result


def test_registers_all_tools():
    tools, _ = build_registry()
    assert set(tools) == EXPECTED_TOOL_NAMES
    assert len(tools) == 27


def test_all_data_tools_happy_path():
    tools, data_source = build_registry()

    calls = {
        "get_historical_k_data": {"code": "sz.000001", "start_date": "2024-01-01", "end_date": "2024-06-30"},
        "get_stock_basic_info": {"code": "sz.000001"},
        "get_dividend_data": {"code": "sz.000001", "year": "2023"},
        "get_adjust_factor_data": {"code": "sz.000001", "start_date": "2024-01-01", "end_date": "2024-06-30"},
        "get_profit_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_operation_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_growth_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_balance_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_cash_flow_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_dupont_data": {"code": "sz.000001", "year": "2024", "quarter": 1},
        "get_performance_express_report": {"code": "sz.000001", "start_date": "2024-01-01", "end_date": "2024-12-31"},
        "get_forecast_report": {"code": "sz.000001", "start_date": "2024-01-01", "end_date": "2024-12-31"},
        "get_stock_industry": {"code": "sz.000001"},
        "get_sz50_stocks": {"date": "2024-06-28"},
        "get_hs300_stocks": {"date": "2024-06-28"},
        "get_zz500_stocks": {"date": "2024-06-28"},
        "get_trade_dates": {"start_date": "2024-06-01", "end_date": "2024-06-30"},
        "get_all_stock": {"date": "2024-06-28"},
        "get_deposit_rate_data": {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        "get_loan_rate_data": {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        "get_required_reserve_ratio_data": {"start_date": "2024-01-01", "end_date": "2024-12-31"},
        "get_money_supply_data_month": {"start_date": "2024-01", "end_date": "2024-06"},
        "get_money_supply_data_year": {"start_date": "2023", "end_date": "2024"},
    }

    for tool_name, kwargs in calls.items():
        result = tools[tool_name](**kwargs)
        assert_markdown_table(result)

    analysis = tools["get_stock_analysis"]("sz.000001", analysis_type="comprehensive")
    assert "数据分析报告" in analysis
    assert "技术面分析" in analysis
    assert "银行" in analysis

    latest_trading_date = tools["get_latest_trading_date"]()
    assert latest_trading_date == "2024-06-28"

    timeframe = tools["get_market_analysis_timeframe"]("quarter")
    assert "ISO日期范围:" in timeframe

    news = tools["crawl_news"]("平安银行", top_k=5)
    assert "新闻结果: 平安银行 (5)" == news

    called_names = {name for name, _ in data_source.calls}
    assert EXPECTED_TOOL_NAMES - {"get_latest_trading_date", "get_market_analysis_timeframe", "get_stock_analysis"} <= called_names


def test_tool_validation_and_error_messages():
    tools, _ = build_registry()

    assert "Invalid frequency" in tools["get_historical_k_data"](
        code="sz.000001",
        start_date="2024-01-01",
        end_date="2024-06-30",
        frequency="bad",
    )
    assert "Invalid adjust_flag" in tools["get_historical_k_data"](
        code="sz.000001",
        start_date="2024-01-01",
        end_date="2024-06-30",
        adjust_flag="9",
    )
    assert "Invalid year_type" in tools["get_dividend_data"](
        code="sz.000001",
        year="2024",
        year_type="bad",
    )
    assert "Invalid year" in tools["get_dividend_data"](
        code="sz.000001",
        year="24",
    )
    assert "Invalid year" in tools["get_profit_data"](
        code="sz.000001",
        year="24",
        quarter=1,
    )
    assert "Invalid quarter" in tools["get_profit_data"](
        code="sz.000001",
        year="2024",
        quarter=5,
    )
    assert "Invalid year_type" in tools["get_required_reserve_ratio_data"](
        year_type="9"
    )
