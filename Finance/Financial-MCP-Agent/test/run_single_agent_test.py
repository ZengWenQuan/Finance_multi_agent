"""
单独测试某一个 Agent 的脚本
用法:
    python test/run_single_agent_test.py --agent fundamental --query "分析比亚迪" --company "比亚迪" --code "002594"
    python test/run_single_agent_test.py --agent technical --query "分析比亚迪" --company "比亚迪" --code "002594"
    python test/run_single_agent_test.py --agent value --query "分析比亚迪" --company "比亚迪" --code "002594"
    python test/run_single_agent_test.py --agent news --query "分析比亚迪" --company "比亚迪" --code "002594"
    python test/run_single_agent_test.py --agent summary --query "分析比亚迪" --company "比亚迪" --code "002594"
    python test/run_single_agent_test.py --agent all --query "分析比亚迪" --company "比亚迪" --code "002594"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test.report_utils import ensure_report_dir, save_agent_report


AGENT_REGISTRY = {
    "fundamental": {
        "func": "src.agents.fundamental_agent.fundamental_agent",
        "data_key": "fundamental_analysis",
        "error_key": "fundamental_analysis_error",
    },
    "technical": {
        "func": "src.agents.technical_agent.technical_agent",
        "data_key": "technical_analysis",
        "error_key": "technical_analysis_error",
    },
    "value": {
        "func": "src.agents.value_agent.value_agent",
        "data_key": "value_analysis",
        "error_key": "value_analysis_error",
    },
    "news": {
        "func": "src.agents.news_agent.news_agent",
        "data_key": "news_analysis",
        "error_key": "news_analysis_error",
    },
    "summary": {
        "func": "src.agents.summary_agent.summary_agent",
        "data_key": "final_report",
        "error_key": "summary_error",
    },
}

AGENT_ORDER = ["fundamental", "technical", "value", "news", "summary"]


def _import_agent_func(func_path: str):
    """动态导入 agent 函数"""
    module_path, func_name = func_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[func_name])
    return getattr(module, func_name)


async def _run_single_agent(agent_name: str, state, timeout_seconds: int) -> tuple:
    """运行单个 agent，返回 (state, success, error_msg)"""
    from src.utils.state_definition import AgentState

    config = AGENT_REGISTRY[agent_name]
    agent_func = _import_agent_func(config["func"])
    data_key = config["data_key"]
    error_key = config["error_key"]

    print(f"\n{'='*60}")
    print(f"  正在运行: {agent_name}")
    print(f"  数据键:   {data_key}")
    print(f"  超时时间: {timeout_seconds}s")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        result_state = await asyncio.wait_for(agent_func(state), timeout=timeout_seconds)
        elapsed = time.time() - start_time
        content = result_state.data.get(data_key, "")
        executed = result_state.metadata.get(f"{agent_name}_executed", False)

        print(f"\n  耗时: {elapsed:.1f}s")
        print(f"  执行成功: {executed}")
        if content:
            preview = content[:200].replace('\n', ' ')
            print(f"  输出预览: {preview}...")

        # 判定成功：metadata 标记为 True，或者输出内容足够长且无错误
        success = executed or (len(content) > 100 and not result_state.data.get(error_key))
        if not success:
            error_msg = result_state.data.get(error_key, "") or content or "unknown failure"
            return result_state, False, error_msg

        # 保存报告
        save_agent_report(agent_name, content, {
            "metadata": result_state.metadata,
            "data_keys": list(result_state.data.keys()),
            "elapsed_seconds": round(elapsed, 1),
        })

        return result_state, True, None

    except TimeoutError:
        elapsed = time.time() - start_time
        error_msg = f"{agent_name} timed out after {timeout_seconds}s"
        print(f"\n  [TIMEOUT] {error_msg}")
        save_agent_report(agent_name, error_msg, {"timeout_seconds": timeout_seconds})
        return state, False, error_msg
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"{type(e).__name__}: {e}"
        print(f"\n  [ERROR] {error_msg}")
        save_agent_report(agent_name, error_msg, {"error": error_msg, "elapsed": round(elapsed, 1)})
        return state, False, error_msg


async def _check_llm_health(base_url: str) -> dict:
    """检查 LLM 服务是否可用"""
    import requests
    health = {"base_url": base_url}
    if base_url:
        models_url = f"{base_url}/models" if not base_url.endswith("/v1") else f"{base_url}/models"
        try:
            resp = requests.get(models_url, timeout=10)
            health["status_code"] = resp.status_code
            health["ok"] = resp.ok
            if resp.ok:
                models = resp.json().get("data", [])
                health["models"] = [m.get("id", "") for m in models[:5]]
                print(f"  LLM 可用，模型列表: {health['models']}")
            else:
                health["error"] = resp.text[:200]
                print(f"  LLM 不可用: status={resp.status_code}")
        except Exception as exc:
            health["ok"] = False
            health["error"] = str(exc)
            print(f"  LLM 连接失败: {exc}")
    else:
        health["ok"] = False
        health["error"] = "BASE_URL not set"
        print(f"  LLM 未配置")
    return health


async def _run(query: str, company: str, code: str, agent_name: str) -> int:
    """主测试流程"""
    report_dir = ensure_report_dir()
    timeout_seconds = int(os.getenv("AGENT_TEST_TIMEOUT_SECONDS", "300"))
    base_url = (os.getenv("OPENAI_COMPATIBLE_BASE_URL_TEST") or os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")).rstrip("/")

    # 1. 检查 LLM 健康状态
    print("\n[1/3] 检查 LLM 服务健康状态...")
    llm_health = await _check_llm_health(base_url)
    (report_dir / "llm_health.json").write_text(
        json.dumps(llm_health, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not llm_health.get("ok") and agent_name != "summary":
        print("\n  [WARNING] LLM 不可用，但继续执行测试（MCP 工具调用可能正常）")

    # 2. 构建初始状态
    print(f"\n[2/3] 构建初始状态...")
    print(f"  查询: {query}")
    print(f"  公司: {company}")
    print(f"  代码: {code}")

    from src.services.query_processing import build_initial_state
    state = build_initial_state(query, company, code)

    # 3. 运行 agent(s)
    print(f"\n[3/3] 运行 Agent 测试...")

    if agent_name == "all":
        # 依次运行所有 4 个分析师 agent + summary
        agents_to_run = AGENT_ORDER
    else:
        agents_to_run = [agent_name]

    failures = []
    for name in agents_to_run:
        state, success, error = await _run_single_agent(name, state, timeout_seconds)
        if not success:
            failures.append(f"{name}: {error}")

    # 汇总
    print(f"\n{'='*60}")
    print(f"  测试结果汇总")
    print(f"{'='*60}")

    if failures:
        print(f"\n  [FAILED] {len(failures)}/{len(agents_to_run)} 个 Agent 失败:")
        for f in failures:
            print(f"    - {f}")
        (report_dir / "single_test_failures.txt").write_text("\n".join(failures), encoding="utf-8")
        return 1
    else:
        print(f"\n  [SUCCESS] 所有 {len(agents_to_run)} 个 Agent 测试通过!")
        (report_dir / "single_test_failures.txt").write_text("", encoding="utf-8")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="单独测试某个 Agent 或全部 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --agent fundamental --query "分析比亚迪" --company "比亚迪" --code "002594"
  %(prog)s --agent all --query "亨通光电怎么样" --company "亨通光电" --code "600487"
  %(prog)s --agent news --query "分析比亚迪新闻" --company "比亚迪" --code "002594"
  %(prog)s --agent summary --query "分析比亚迪" --company "比亚迪" --code "002594"
        """,
    )
    parser.add_argument(
        "--agent",
        choices=["fundamental", "technical", "value", "news", "summary", "all"],
        required=True,
        help="要测试的 Agent 名称，或 'all' 运行全部",
    )
    parser.add_argument("--query", default="分析比亚迪股票怎么样", help="查询文本")
    parser.add_argument("--company", default="比亚迪", help="公司名称")
    parser.add_argument("--code", default="002594", help="股票代码（6位纯数字）")
    args = parser.parse_args()
    return asyncio.run(_run(args.query, args.company, args.code, args.agent))


if __name__ == "__main__":
    raise SystemExit(main())
