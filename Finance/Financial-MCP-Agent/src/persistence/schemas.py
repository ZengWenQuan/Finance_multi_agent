from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    id: int | None = None
    session_name: str
    company_name: str | None = None
    stock_code: str | None = None
    user_query: str
    status: str = "completed"
    source: str = "cli"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentResultRecord(BaseModel):
    id: int | None = None
    session_id: int
    agent_name: str
    schema_version: str = "v1"
    display_title: str
    content: str = ""
    structured_data_json: dict[str, Any] = Field(default_factory=dict)
    execution_trace_json: dict[str, Any] = Field(default_factory=dict)
    raw_context_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ReportRecord(BaseModel):
    id: int | None = None
    session_id: int
    final_report: str
    report_path: str | None = None
    report_markdown_snapshot: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatMessageRecord(BaseModel):
    id: int | None = None
    session_id: int
    role: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FundamentalStructuredData(BaseModel):
    """基本面分析结构化数据，包含指标卡片和表格所需字段"""
    company_name: str | None = None
    stock_code: str | None = None
    analysis_text: str = ""
    execution_time: str | None = None
    executed: bool = False
    error: str | None = None
    # 前端可视化字段（第二阶段补齐）
    company_profile: str | None = None
    financial_statement_summary: str | None = None
    profitability_metrics: dict[str, Any] | None = None   # {营业收入, 净利润, ROE, ROA, 毛利率, 净利率}
    growth_metrics: dict[str, Any] | None = None          # {营收增速, 净利增速, ...}
    operating_efficiency_metrics: dict[str, Any] | None = None
    solvency_metrics: dict[str, Any] | None = None        # {资产负债率, 流动比率, ...}
    dividend_summary: str | None = None
    investment_conclusion: str | None = None
    risk_flags: list[str] | None = None


class TechnicalStructuredData(BaseModel):
    """技术分析结构化数据，包含趋势摘要卡片所需字段"""
    company_name: str | None = None
    stock_code: str | None = None
    analysis_text: str = ""
    execution_time: str | None = None
    executed: bool = False
    error: str | None = None
    # 前端可视化字段（第二阶段补齐）
    latest_price_summary: dict[str, Any] | None = None    # {最新价, 涨跌幅, 成交量, 换手率}
    historical_kline_summary: str | None = None
    trend_analysis: str | None = None                     # 趋势判断文字：上升/下降/震荡
    volume_analysis: str | None = None
    indicator_summary: dict[str, Any] | None = None       # {MACD, KDJ, RSI, ...}
    support_levels: list[float] | None = None
    resistance_levels: list[float] | None = None
    short_term_signal: str | None = None                  # 买/卖/持有/观望


class ValueStructuredData(BaseModel):
    """估值分析结构化数据，包含估值对比卡片所需字段"""
    company_name: str | None = None
    stock_code: str | None = None
    analysis_text: str = ""
    execution_time: str | None = None
    executed: bool = False
    error: str | None = None
    # 前端可视化字段（第二阶段补齐）
    market_value_summary: dict[str, Any] | None = None    # {总市值, 流通市值}
    valuation_metrics: dict[str, Any] | None = None       # {PE, PB, PS, EV/EBITDA}
    peer_comparison: list[dict[str, Any]] | None = None   # [{公司, PE, PB}, ...]
    historical_valuation_trend: str | None = None
    dividend_yield_summary: dict[str, Any] | None = None  # {股息率, 每股分红}
    intrinsic_value_assessment: str | None = None
    valuation_conclusion: str | None = None               # 低估/合理/高估


class NewsStructuredData(BaseModel):
    """新闻分析结构化数据，包含新闻列表和情绪标签所需字段"""
    company_name: str | None = None
    stock_code: str | None = None
    analysis_text: str = ""
    execution_time: str | None = None
    executed: bool = False
    error: str | None = None
    # 前端可视化字段（第二阶段补齐）
    news_items: list[dict[str, Any]] | None = None        # [{title, source, url, summary, sentiment_score}]
    sentiment_summary: str | None = None                  # 整体情绪：正面/中性/负面
    sentiment_score: float | None = None                  # -1.0 ~ 1.0
    risk_summary: str | None = None
    price_impact_summary: str | None = None
    key_events: list[str] | None = None
    news_based_conclusion: str | None = None


class SummaryStructuredData(BaseModel):
    """综合报告结构化数据"""
    company_name: str | None = None
    stock_code: str | None = None
    report_path: str | None = None
    final_report: str = ""
    execution_time: str | None = None
    executed: bool = False
    error: str | None = None
    # 前端可视化字段（第二阶段补齐）
    executive_summary: str | None = None
    overall_assessment: str | None = None                 # 综合评级
    recommendation_section: str | None = None             # 投资建议
    risk_section: str | None = None

