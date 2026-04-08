from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.fundamental_agent import fundamental_agent
from src.agents.news_agent import news_agent
from src.agents.summary_agent import summary_agent
from src.agents.technical_agent import technical_agent
from src.agents.value_agent import value_agent
from src.services.query_processing import build_initial_state, extract_entities_from_query
from test.report_utils import ensure_report_dir, save_agent_report


AGENTS = [
    ("fundamental_agent", fundamental_agent, "fundamental_analysis", "fundamental_analysis_error"),
    ("technical_agent", technical_agent, "technical_analysis", "technical_analysis_error"),
    ("value_agent", value_agent, "value_analysis", "value_analysis_error"),
    ("news_agent", news_agent, "news_analysis", "news_analysis_error"),
]


async def _run(query: str, expected_company: str, expected_code: str) -> int:
    report_dir = ensure_report_dir()
    timeout_seconds = int(os.getenv("AGENT_TEST_TIMEOUT_SECONDS", "90"))
    base_url = (os.getenv("OPENAI_COMPATIBLE_BASE_URL_TEST") or os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")).rstrip("/")

    llm_health = {"base_url": base_url}
    if base_url:
        models_url = f"{base_url}/models" if not base_url.endswith("/v1") else f"{base_url}/models"
        try:
            response = requests.get(models_url, timeout=10)
            llm_health["status_code"] = response.status_code
            llm_health["ok"] = response.ok
            llm_health["body_preview"] = response.text[:500]
        except Exception as exc:
            llm_health["ok"] = False
            llm_health["error"] = str(exc)
    else:
        llm_health["ok"] = False
        llm_health["error"] = "OPENAI_COMPATIBLE_BASE_URL_TEST/OPENAI_COMPATIBLE_BASE_URL is not set"

    (report_dir / "llm_health.json").write_text(
        json.dumps(llm_health, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    extracted_company, extracted_code = await asyncio.wait_for(
        extract_entities_from_query(query),
        timeout=timeout_seconds,
    )
    entity_payload = {
        "query": query,
        "expected_company": expected_company,
        "expected_code": expected_code,
        "extracted_company": extracted_company,
        "extracted_code": extracted_code,
    }
    (report_dir / "entity_extraction.json").write_text(
        json.dumps(entity_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    company_name = extracted_company or expected_company
    stock_code = extracted_code or expected_code
    state = build_initial_state(query, company_name, stock_code)

    failures: list[str] = []
    for agent_name, agent_func, data_key, error_key in AGENTS:
        try:
            state = await asyncio.wait_for(agent_func(state), timeout=timeout_seconds)
            content = state.data.get(data_key, "")
            save_agent_report(agent_name, content, {"metadata": state.metadata, "data": state.data})
            if not state.metadata.get(f"{agent_name}_executed"):
                failures.append(f"{agent_name}: {state.data.get(error_key) or state.data.get(data_key) or 'unknown failure'}")
        except TimeoutError:
            timeout_message = f"{agent_name} timed out after {timeout_seconds}s"
            save_agent_report(agent_name, timeout_message, {"timeout_seconds": timeout_seconds})
            failures.append(timeout_message)

    try:
        state = await asyncio.wait_for(summary_agent(state), timeout=timeout_seconds)
        save_agent_report("summary_agent", state.data.get("final_report", ""), {"metadata": state.metadata, "data": state.data})
    except TimeoutError:
        timeout_message = f"summary_agent timed out after {timeout_seconds}s"
        save_agent_report("summary_agent", timeout_message, {"timeout_seconds": timeout_seconds})
        failures.append(timeout_message)

    if extracted_company != expected_company:
        failures.append(f"entity extraction company mismatch: expected={expected_company}, actual={extracted_company}")
    if extracted_code != expected_code:
        failures.append(f"entity extraction code mismatch: expected={expected_code}, actual={extracted_code}")

    if failures:
        (report_dir / "real_test_failures.txt").write_text("\n".join(failures), encoding="utf-8")
        return 1

    (report_dir / "real_test_failures.txt").write_text("", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real agent tests and persist outputs.")
    parser.add_argument("--query", default="分析比亚迪股票怎么样")
    parser.add_argument("--company", default="比亚迪")
    parser.add_argument("--code", default="002594")
    args = parser.parse_args()
    return asyncio.run(_run(args.query, args.company, args.code))


if __name__ == "__main__":
    raise SystemExit(main())
