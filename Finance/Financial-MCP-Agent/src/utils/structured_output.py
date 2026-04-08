from __future__ import annotations

from typing import Type

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel


def _build_fallback_output(
    schema_cls: Type[BaseModel],
    company_name: str | None,
    stock_code: str | None,
    raw_analysis: str,
    issue: str | None = None,
) -> BaseModel:
    payload: dict[str, object] = {}
    model_fields = getattr(schema_cls, "model_fields", {})

    if "company_name" in model_fields:
        payload["company_name"] = company_name
    if "stock_code" in model_fields:
        payload["stock_code"] = stock_code
    if "summary" in model_fields:
        payload["summary"] = raw_analysis.strip()[:500] if raw_analysis else None
    if "raw_analysis" in model_fields:
        payload["raw_analysis"] = raw_analysis
    if "missing_data" in model_fields and issue:
        payload["missing_data"] = [issue]
    if "data_limitations" in model_fields and issue:
        payload["data_limitations"] = [issue]

    return schema_cls.model_validate(payload)


async def build_structured_output(
    llm,
    schema_cls: Type[BaseModel],
    agent_label: str,
    company_name: str | None,
    stock_code: str | None,
    raw_analysis: str,
    issue: str | None = None,
) -> BaseModel:
    if not hasattr(llm, "with_structured_output"):
        return _build_fallback_output(schema_cls, company_name, stock_code, raw_analysis, issue)

    structured_llm = llm.with_structured_output(schema_cls)
    messages = [
        SystemMessage(
            content=(
                f"你是一个严格的结构化信息整理器。"
                f"请把{agent_label}的自然语言分析整理为给定 schema。"
                f"只能依据输入内容提取信息，不要补造数据。"
                f"如果某项没有足够依据，请留空或放入 missing_data/data_limitations。"
            )
        ),
        HumanMessage(
            content=(
                f"公司名称: {company_name or 'Unknown'}\n"
                f"股票代码: {stock_code or 'Unknown'}\n"
                f"当前已知问题: {issue or 'None'}\n\n"
                f"{agent_label}原始分析如下:\n{raw_analysis}"
            )
        ),
    ]

    try:
        result = await structured_llm.ainvoke(messages)
        if getattr(result, "company_name", None) in (None, "", "Unknown"):
            if hasattr(result, "company_name"):
                result.company_name = company_name
        if getattr(result, "stock_code", None) in (None, "", "Unknown"):
            if hasattr(result, "stock_code"):
                result.stock_code = stock_code
        if hasattr(result, "raw_analysis") and not getattr(result, "raw_analysis", None):
            result.raw_analysis = raw_analysis
        if issue:
            if hasattr(result, "missing_data"):
                existing = list(getattr(result, "missing_data", []) or [])
                if issue not in existing:
                    existing.append(issue)
                result.missing_data = existing
            if hasattr(result, "data_limitations"):
                existing = list(getattr(result, "data_limitations", []) or [])
                if issue not in existing:
                    existing.append(issue)
                result.data_limitations = existing
        return result
    except Exception:
        return _build_fallback_output(schema_cls, company_name, stock_code, raw_analysis, issue)
