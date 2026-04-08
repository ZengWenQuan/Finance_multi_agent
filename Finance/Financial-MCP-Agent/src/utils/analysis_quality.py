from __future__ import annotations

import re
from dataclasses import dataclass


INVALID_OUTPUT_PATTERNS = [
    r"^\s*$",
    r"no analysis generated",
    r"sorry,\s*need more steps",
    r"connection error",
    r"系统未登录",
    r"未登录",
    r"返回空结果",
    r"查询失败",
    r"无法获取",
    r"未能获取",
    r"没有获取到",
    r"failed to",
    r"error in mcp or agent execution",
]

COMPANY_NAME_NOISE_PATTERNS = [
    r"股票怎么样",
    r"股票如何",
    r"这只股票怎么样",
    r"这个股票怎么样",
    r"这只股票",
    r"这个股票",
    r"这只",
    r"这个",
    r"怎么样",
    r"的报告",
    r"报告",
    r"分析一下",
    r"分析下",
    r"分析",
    r"帮我看看",
    r"帮我分析一下",
    r"帮我分析",
    r"请帮我分析一下",
    r"请帮我分析",
    r"我想了解一下",
    r"给我分析一下",
    r"给我分析",
]


@dataclass
class AnalysisCheck:
    is_valid: bool
    issue: str | None = None


def sanitize_company_name(name: str | None) -> str | None:
    if not name:
        return None

    value = str(name).strip()
    for pattern in COMPANY_NAME_NOISE_PATTERNS:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    value = re.sub(r"[，,。！？!?.（）()\[\]【】]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip("的了是")

    return value if len(value) >= 2 else None


def extract_analysis_text(response: object) -> str:
    if not isinstance(response, dict):
        return "No analysis generated."

    messages = response.get("messages")
    if not isinstance(messages, list):
        return "No analysis generated."

    for message in reversed(messages):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()

    return "No analysis generated."


def validate_analysis_output(output: str) -> AnalysisCheck:
    normalized = (output or "").strip()
    lowered = normalized.lower()

    if len(normalized) < 12:
        return AnalysisCheck(False, "analysis output is too short")

    for pattern in INVALID_OUTPUT_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return AnalysisCheck(False, f"analysis output matched invalid pattern: {pattern}")

    return AnalysisCheck(True, None)


def build_agent_failure_message(agent_label: str, issue: str, raw_output: str | None = None) -> str:
    message = f"{agent_label}未获得可用的真实分析结果：{issue}。"
    if raw_output:
        preview = raw_output.strip().replace("\n", " ")
        if len(preview) > 180:
            preview = preview[:180] + "..."
        message += f"\n原始输出：{preview}"
    return message
