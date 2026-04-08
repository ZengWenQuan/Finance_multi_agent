"""
定义每个 Agent 的工具白名单，以及 Agent 到工具列表的映射关系。
"""

# 每个 Agent 只维护一份工具列表，避免重复定义和多处同步。

fundamental_agent = [
    "get_latest_trading_date",
    "get_market_analysis_timeframe",
    "get_stock_basic_info",
    "get_stock_industry",
    "get_profit_data",
    "get_operation_data",
    "get_growth_data",
    "get_balance_data",
    "get_cash_flow_data",
]

news_agent = [
    "get_latest_trading_date",
    "get_stock_basic_info",
    "crawl_news",
    "search_company_news",
    "search_industry_news",
]

technical_agent = [
    "get_latest_trading_date",
    "get_market_analysis_timeframe",
    "get_historical_k_data",
    "get_stock_basic_info",
    "get_adjust_factor_data",
    "get_all_stock",                # 新增：全量股票列表
    "get_hs300_stocks",             # 新增：沪深300
    "get_sz50_stocks",              # 新增：上证50
    "get_zz500_stocks",             # 新增：中证500
    "get_trade_dates",              # 新增：交易日历
]

value_agent = [
    "get_latest_trading_date",
    "get_stock_basic_info",
    "get_historical_k_data",
    "get_dividend_data",
    "get_dupont_data",
    "get_deposit_rate_data",             # 新增：宏观存款利率
    "get_loan_rate_data",                # 新增：宏观贷款利率
    "get_money_supply_data_month",       # 新增：货币供应(月)
    "get_money_supply_data_year",        # 新增：货币供应(年)
    "get_required_reserve_ratio_data",   # 新增：存款准备金率
]

summary_agent = [
    "get_stock_analysis",
]


AGENT_TOOL_MAPPING = {
    "fundamental_agent": fundamental_agent,
    "news_agent": news_agent,
    "technical_agent": technical_agent,
    "value_agent": value_agent,
    "summary_agent": summary_agent,
}


def get_tools_for_agent(agent_name: str, available_tools: list) -> list:
    """
    根据给定的 agent 名称，从所有可用工具中过滤出该 agent 的专属工具列表。
    """
    if agent_name not in AGENT_TOOL_MAPPING:
        print(f"Warning: agent '{agent_name}' not found in mapping, returning no tools.")
        return []

    allowed_tool_names = set(AGENT_TOOL_MAPPING[agent_name])
    return [tool for tool in available_tools if tool.name in allowed_tool_names]
