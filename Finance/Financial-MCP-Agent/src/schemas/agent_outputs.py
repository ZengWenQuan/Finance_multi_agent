from __future__ import annotations

from pydantic import BaseModel, Field


class AgentStructuredOutput(BaseModel):
    company_name: str | None = None
    stock_code: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    major_risks: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    raw_analysis: str | None = None


class FundamentalAnalysisOutput(AgentStructuredOutput):
    profitability_view: str | None = None
    growth_view: str | None = None
    solvency_view: str | None = None
    operation_view: str | None = None
    shareholder_return_view: str | None = None


class TechnicalAnalysisOutput(AgentStructuredOutput):
    trend_view: str | None = None
    momentum_view: str | None = None
    volume_view: str | None = None
    support_resistance_view: str | None = None
    short_term_outlook: str | None = None


class ValueAnalysisOutput(AgentStructuredOutput):
    valuation_view: str | None = None
    relative_valuation_view: str | None = None
    historical_valuation_view: str | None = None
    shareholder_return_view: str | None = None
    investment_view: str | None = None


class NewsAnalysisOutput(AgentStructuredOutput):
    sentiment_view: str | None = None
    risk_view: str | None = None
    market_impact_view: str | None = None
    key_events: list[str] = Field(default_factory=list)
    investment_view: str | None = None


class SummaryAnalysisOutput(AgentStructuredOutput):
    investment_thesis: str | None = None
    recommendation: str | None = None
    confidence: str | None = None
    catalysts: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
