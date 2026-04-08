"""
Agent 指标评估脚本
从 SQLite 和执行日志中批量计算各维度量化指标。

用法：
    conda run -n lamost python -m src.eval_metrics                # 评估全部
    conda run -n lamost python -m src.eval_metrics --last 5       # 评估最近 5 次 session
    conda run -n lamost python -m src.eval_metrics --session 23   # 评估指定 session
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "financial_sessions.db"
LOGS_DIR = PROJECT_ROOT / "logs"


# ──────────────────────────────────────────────
# 1. 从 SQLite 计算的指标
# ──────────────────────────────────────────────

def _connect():
    return sqlite3.connect(DB_PATH)


def calc_agent_success_rate(session_ids: list[int] | None = None) -> dict:
    """各 Agent 的成功/失败/超时率"""
    conn = _connect()
    where = ""
    params: list = []
    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        where = f"WHERE session_id IN ({placeholders})"
        params = session_ids

    rows = conn.execute(
        f"""
        SELECT agent_name, status, COUNT(*) as cnt
        FROM agent_results
        {where}
        GROUP BY agent_name, status
        """,
        params,
    ).fetchall()

    conn.close()

    result = {}
    for agent, status, cnt in rows:
        result.setdefault(agent, {"completed": 0, "failed": 0, "total": 0})
        if status == "completed":
            result[agent]["completed"] = cnt
        else:
            result[agent]["failed"] += cnt
        result[agent]["total"] += cnt

    for agent, v in result.items():
        total = v["total"]
        v["success_rate"] = v["completed"] / total if total else 0
    return result


def calc_session_status(session_ids: list[int] | None = None) -> dict:
    """Session 状态分布"""
    conn = _connect()
    where = ""
    params: list = []
    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        where = f"WHERE id IN ({placeholders})"
        params = session_ids

    rows = conn.execute(
        f"""
        SELECT status, COUNT(*) as cnt
        FROM sessions
        {where}
        GROUP BY status
        """,
        params,
    ).fetchall()
    conn.close()
    return {status: cnt for status, cnt in rows}


def calc_end_to_end_latency(session_ids: list[int] | None = None) -> dict:
    """端到端延迟（session created_at → updated_at）"""
    conn = _connect()
    where = ""
    params: list = []
    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        where = f"WHERE id IN ({placeholders})"
        params = session_ids

    rows = conn.execute(
        f"""
        SELECT id, company_name, stock_code,
               created_at, updated_at
        FROM sessions
        {where}
        ORDER BY id DESC
        """,
        params,
    ).fetchall()
    conn.close()

    latencies = []
    for sid, name, code, t_start, t_end in rows:
        try:
            from datetime import datetime
            dt_s = datetime.fromisoformat(t_start)
            dt_e = datetime.fromisoformat(t_end)
            delta = (dt_e - dt_s).total_seconds()
            latencies.append({
                "session_id": sid,
                "company": name or "?",
                "code": code or "?",
                "seconds": round(delta, 1),
            })
        except Exception:
            pass

    if not latencies:
        return {"count": 0}

    values = [l["seconds"] for l in latencies]
    return {
        "count": len(values),
        "avg": round(sum(values) / len(values), 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
        "latest_3": latencies[:3],
    }


def calc_field_fill_rate(session_ids: list[int] | None = None) -> dict:
    """结构化输出字段填充率（非 None / 非空字段占比）"""
    # 每个 Agent Schema 中需要统计的字段
    schema_fields = {
        "fundamental_agent": [
            "company_profile", "financial_statement_summary",
            "profitability_metrics", "growth_metrics",
            "operating_efficiency_metrics", "solvency_metrics",
            "dividend_summary", "investment_conclusion",
        ],
        "technical_agent": [
            "latest_price_summary", "historical_kline_summary",
            "trend_analysis", "volume_analysis",
            "indicator_summary", "short_term_signal",
        ],
        "value_agent": [
            "market_value_summary", "valuation_metrics",
            "peer_comparison", "dividend_yield_summary",
            "intrinsic_value_assessment", "valuation_conclusion",
        ],
        "news_agent": [
            "news_items", "sentiment_summary", "sentiment_score",
            "risk_summary", "price_impact_summary", "key_events",
        ],
        "summary_agent": [
            "executive_summary", "overall_assessment",
            "recommendation_section", "risk_section",
        ],
    }

    conn = _connect()
    where = ""
    params: list = []
    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        where = f"WHERE session_id IN ({placeholders})"
        params = session_ids

    rows = conn.execute(
        f"""
        SELECT agent_name, structured_data_json
        FROM agent_results
        {where}
        """,
        params,
    ).fetchall()
    conn.close()

    result = {}
    for agent_name, raw_json in rows:
        if agent_name not in schema_fields:
            continue
        fields = schema_fields[agent_name]
        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception:
            data = {}

        filled = sum(1 for f in fields if data.get(f) is not None and data.get(f) != "" and data.get(f) != [])
        total = len(fields)
        rate = filled / total if total else 0
        result.setdefault(agent_name, []).append({"filled": filled, "total": total, "rate": round(rate, 2)})

    # 聚合
    summary = {}
    for agent, entries in result.items():
        rates = [e["rate"] for e in entries]
        summary[agent] = {
            "sessions": len(entries),
            "avg_fill_rate": round(sum(rates) / len(rates), 2),
            "min_fill_rate": round(min(rates), 2),
        }
    return summary


# ──────────────────────────────────────────────
# 2. 从执行日志（JSONL）计算的指标
# ──────────────────────────────────────────────

def calc_tool_metrics_from_logs(log_dir: Path | None = None) -> dict:
    """从 logs/ 目录的各执行子目录中的 tools/*.jsonl 计算工具成功率、延迟"""
    base = log_dir or LOGS_DIR
    # 搜索所有执行子目录下的 tools/*.jsonl
    jsonl_files = sorted(base.glob("*/tools/*.jsonl")) + sorted((base / "tools").glob("*.jsonl"))
    if not jsonl_files:
        return {"error": "未找到工具日志文件，请先运行至少一次分析"}

    stats = {}
    for jsonl_file in jsonl_files:
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                tool = entry.get("tool_name", "unknown")
                success = entry.get("success", False)
                elapsed = entry.get("execution_time_seconds", 0)
                stats.setdefault(tool, {"success": 0, "fail": 0, "total_time": 0, "count": 0})
                if success:
                    stats[tool]["success"] += 1
                else:
                    stats[tool]["fail"] += 1
                stats[tool]["total_time"] += elapsed
                stats[tool]["count"] += 1

    # 计算成功率
    for tool, v in stats.items():
        total = v["success"] + v["fail"]
        v["success_rate"] = v["success"] / total if total else 0
        v["avg_latency"] = round(v["total_time"] / v["count"], 2) if v["count"] else 0
        del v["total_time"]

    return stats


def calc_llm_token_usage(log_dir: Path | None = None) -> dict:
    """从 logs/ 目录的各执行子目录中的 llm_interactions/*.json 计算 Token 消耗"""
    base = log_dir or LOGS_DIR
    json_files = sorted(base.glob("*/llm_interactions/*.json")) + sorted((base / "llm_interactions").glob("*.json"))
    if not json_files:
        return {"error": "未找到 LLM 交互日志，请先运行至少一次分析"}

    total_prompt = 0
    total_completion = 0
    file_count = 0
    per_agent: dict = {}

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        file_count += 1
        agent = data.get("agent_name", "unknown")
        usage = data.get("performance", {}).get("token_usage") or {}

        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        total_prompt += prompt_tokens
        total_completion += completion_tokens

        per_agent.setdefault(agent, {"prompt": 0, "completion": 0, "files": 0})
        per_agent[agent]["prompt"] += prompt_tokens
        per_agent[agent]["completion"] += completion_tokens
        per_agent[agent]["files"] += 1

    return {
        "total_files": file_count,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "per_agent": per_agent,
    }


# ──────────────────────────────────────────────
# 3. 工具利用率
# ──────────────────────────────────────────────

def calc_tool_utilization() -> dict:
    """统计各 Agent 白名单中工具的实际利用率"""
    try:
        from src.tools.agent_tool_mapping import AGENT_TOOL_MAPPING
    except ImportError:
        return {"error": "无法导入 agent_tool_mapping"}

    tool_metrics = calc_tool_metrics_from_logs()
    if "error" in tool_metrics:
        return tool_metrics

    result = {}
    for agent, allowed in AGENT_TOOL_MAPPING.items():
        used = {t for t in tool_metrics if t in allowed}
        result[agent] = {
            "allowed": len(allowed),
            "actually_used": len(used),
            "utilization_rate": round(len(used) / len(allowed), 2) if allowed else 0,
            "used_tools": sorted(used),
            "unused_tools": sorted(set(allowed) - used),
        }
    return result


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────

def print_section(title: str, data: dict):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Agent 指标评估")
    parser.add_argument("--last", type=int, default=0, help="评估最近 N 次 session")
    parser.add_argument("--session", type=int, default=0, help="评估指定 session_id")
    args = parser.parse_args()

    # 确定 session 范围
    session_ids = None
    if args.session:
        session_ids = [args.session]
    elif args.last:
        conn = _connect()
        rows = conn.execute(
            "SELECT id FROM sessions ORDER BY id DESC LIMIT ?", (args.last,)
        ).fetchall()
        conn.close()
        session_ids = [r[0] for r in rows]
        print(f"评估最近 {args.last} 次 session: {session_ids}")

    # 1. Agent 成功率
    print_section("Agent 成功率", calc_agent_success_rate(session_ids))

    # 2. Session 状态分布
    print_section("Session 状态分布", calc_session_status(session_ids))

    # 3. 端到端延迟
    print_section("端到端延迟（秒）", calc_end_to_end_latency(session_ids))

    # 4. 字段填充率
    print_section("结构化字段填充率", calc_field_fill_rate(session_ids))

    # 5. 工具成功率 + 延迟
    print_section("工具成功率 & 平均延迟", calc_tool_metrics_from_logs())

    # 6. 工具利用率
    tool_data = calc_tool_metrics_from_logs()
    if "error" not in tool_data:
        try:
            from src.tools.agent_tool_mapping import AGENT_TOOL_MAPPING
            result = {}
            for agent, allowed in AGENT_TOOL_MAPPING.items():
                used = {t for t in tool_data if t in allowed}
                result[agent] = {
                    "allowed": len(allowed),
                    "actually_used": len(used),
                    "utilization_rate": round(len(used) / len(allowed), 2) if allowed else 0,
                    "used_tools": sorted(used),
                    "unused_tools": sorted(set(allowed) - used),
                }
            print_section("工具白名单利用率", result)
        except ImportError:
            pass
    else:
        print_section("工具白名单利用率", tool_data)

    # 7. Token 消耗
    print_section("LLM Token 消耗", calc_llm_token_usage())


if __name__ == "__main__":
    main()
