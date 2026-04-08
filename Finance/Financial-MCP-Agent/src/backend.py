from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.persistence.schemas import ChatMessageRecord, SessionRecord
from src.services.analysis_service import (
    AGENT_CONFIG,
    persist_single_agent_result,
    persist_report_only,
    get_default_store,
    get_default_vector_service,
    get_default_graph_store,
)
from src.services.chat_service import chat_with_session_context
from src.services.query_processing import build_initial_state, extract_entities_from_query
from src.utils.execution_logger import finalize_execution_logger, initialize_execution_logger
from src.utils.state_definition import AgentState

logger = logging.getLogger(__name__)

TASK_TIMEOUT_SECONDS = 600  # 单个 agent 最大执行时间 10 分钟


app = FastAPI(title="Financial MCP Agent Backend", version="0.2.0")
store = get_default_store()
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

# ---------- 内存态任务追踪 ----------
TASKS: dict[str, dict[str, Any]] = {}

# 每个 session 对应一个 execution_dir 和 AgentState
SESSION_STATE: dict[int, dict[str, Any]] = {}

ANALYST_AGENTS = ["fundamental_agent", "technical_agent", "value_agent", "news_agent"]

# Agent 函数引用（延迟导入避免循环）
_AGENT_FUNCS: dict[str, Any] = {}


def _get_agent_func(agent_name: str):
    if not _AGENT_FUNCS:
        from src.agents.fundamental_agent import fundamental_agent
        from src.agents.technical_agent import technical_agent
        from src.agents.value_agent import value_agent
        from src.agents.news_agent import news_agent
        from src.agents.summary_agent import summary_agent
        _AGENT_FUNCS.update({
            "fundamental_agent": fundamental_agent,
            "technical_agent": technical_agent,
            "value_agent": value_agent,
            "news_agent": news_agent,
            "summary_agent": summary_agent,
        })
    func = _AGENT_FUNCS.get(agent_name)
    if not func:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_name}")
    return func


# ---------- Pydantic Models ----------
class CreateSessionRequest(BaseModel):
    user_query: str
    session_name: str | None = None
    company_name: str | None = None
    stock_code: str | None = None
    source: str = "web"


class CreateChatRequest(BaseModel):
    role: str = "user"
    content: str
    rag_mode: str = "c8_hybrid_rag"


class ParseRequest(BaseModel):
    user_query: str


# ---------- 分步执行逻辑 ----------
async def _run_single_agent(session_id: int, agent_name: str, task_id: str):
    """单独运行一个分析师 agent 并持久化结果"""
    ctx = SESSION_STATE.get(session_id)
    if not ctx:
        TASKS[task_id]["agent_status"][agent_name] = "failed"
        TASKS[task_id]["agent_status"][agent_name + "_error"] = "Session state lost"
        return

    state = ctx["state"]
    execution_dir = ctx["execution_dir"]

    try:
        agent_func = _get_agent_func(agent_name)
        TASKS[task_id]["agent_status"][agent_name] = "running"
        result_state = await asyncio.wait_for(
            agent_func(state), timeout=TASK_TIMEOUT_SECONDS
        )
        # 更新共享 state
        SESSION_STATE[session_id]["state"] = result_state
        # 持久化
        persist_single_agent_result(agent_name, result_state, execution_dir, session_id, store)
        TASKS[task_id]["agent_status"][agent_name] = "completed"

        # 检查是否所有分析师都完成了
        if all(TASKS[task_id]["agent_status"].get(a) == "completed" for a in ANALYST_AGENTS):
            TASKS[task_id]["agent_status"]["summary_agent"] = "ready"

    except asyncio.TimeoutError:
        msg = f"{agent_name} 执行超时"
        logger.error(f"Session {session_id} agent {agent_name}: {msg}")
        TASKS[task_id]["agent_status"][agent_name] = "failed"
        TASKS[task_id]["agent_status"][agent_name + "_error"] = msg
    except Exception as e:
        logger.error(f"Session {session_id} agent {agent_name}: {e}", exc_info=True)
        TASKS[task_id]["agent_status"][agent_name] = "failed"
        TASKS[task_id]["agent_status"][agent_name + "_error"] = str(e)


async def _run_summary(session_id: int, task_id: str):
    """运行综合报告 agent"""
    ctx = SESSION_STATE.get(session_id)
    if not ctx:
        TASKS[task_id]["agent_status"]["summary_agent"] = "failed"
        return

    state = ctx["state"]
    execution_dir = ctx["execution_dir"]
    user_query = state.data.get("query", "")

    try:
        summary_func = _get_agent_func("summary_agent")
        TASKS[task_id]["agent_status"]["summary_agent"] = "running"
        result_state = await asyncio.wait_for(
            summary_func(state), timeout=TASK_TIMEOUT_SECONDS
        )
        SESSION_STATE[session_id]["state"] = result_state

        # 持久化
        persist_single_agent_result("summary_agent", result_state, execution_dir, session_id, store)
        persist_report_only(
            result_state, session_id, store,
            get_default_vector_service(), get_default_graph_store(),
            ctx.get("source", "web"), user_query, execution_dir,
        )
        store.update_session_status(session_id, "completed")

        TASKS[task_id]["agent_status"]["summary_agent"] = "completed"
        TASKS[task_id]["status"] = "completed"
        TASKS[task_id]["report_path"] = result_state.data.get("report_path")
        finalize_execution_logger(success=True)

    except asyncio.TimeoutError:
        msg = "综合报告生成超时"
        logger.error(f"Session {session_id} summary: {msg}")
        TASKS[task_id]["agent_status"]["summary_agent"] = "failed"
        store.update_session_status(session_id, "failed")
        finalize_execution_logger(success=False, error=msg)
    except Exception as e:
        logger.error(f"Session {session_id} summary: {e}", exc_info=True)
        TASKS[task_id]["agent_status"]["summary_agent"] = "failed"
        store.update_session_status(session_id, "failed")
        finalize_execution_logger(success=False, error=str(e))


# ---------- API Endpoints ----------

@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def frontend_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    return store.list_sessions()


@app.post("/api/sessions")
async def create_session(payload: CreateSessionRequest) -> dict[str, Any]:
    """创建 session（不自动启动分析），前端接下来应调用 /parse"""
    session_id = store.create_session(
        SessionRecord(
            session_name=payload.session_name or payload.company_name or payload.stock_code or payload.user_query[:24],
            company_name=payload.company_name,
            stock_code=payload.stock_code,
            user_query=payload.user_query,
            status="pending",
            source=payload.source,
        )
    )
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "task_id": task_id,
        "session_id": session_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "error": None,
        "agent_status": {
            "parse": "pending",
            "fundamental_agent": "locked",
            "technical_agent": "locked",
            "value_agent": "locked",
            "news_agent": "locked",
            "summary_agent": "locked",
        },
    }
    return {"session_id": session_id, "task_id": task_id, "status": "pending"}


@app.post("/api/sessions/{session_id}/parse")
async def parse_query(session_id: int, payload: ParseRequest) -> dict[str, Any]:
    """步骤1：解析用户查询，提取公司名和股票代码"""
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 找到该 session 对应的 task
    task = next((t for t in TASKS.values() if t["session_id"] == session_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for session")
    task_id = task["task_id"]

    task["agent_status"]["parse"] = "running"

    try:
        company_name, stock_code = await extract_entities_from_query(payload.user_query)
        if not company_name and not stock_code:
            task["agent_status"]["parse"] = "failed"
            task["agent_status"]["parse_error"] = "未能识别公司名或股票代码"
            return {
                "session_id": session_id,
                "company_name": None,
                "stock_code": None,
                "status": "failed",
                "error": "未能从输入中识别出公司名称或股票代码",
            }

        # 构建 AgentState
        initial_state = build_initial_state(payload.user_query, company_name, stock_code)
        execution_logger = initialize_execution_logger()

        # 保存到 SESSION_STATE
        SESSION_STATE[session_id] = {
            "state": initial_state,
            "execution_dir": str(execution_logger.execution_dir),
            "source": "web",
        }

        # 更新 session 记录
        store.update_session_details(
            session_id=session_id,
            session_name=company_name or stock_code or session.get("session_name"),
            company_name=company_name,
            stock_code=stock_code,
            user_query=payload.user_query,
            status="parsed",
            source="web",
        )

        task["agent_status"]["parse"] = "completed"
        # 解锁分析师按钮
        for a in ANALYST_AGENTS:
            task["agent_status"][a] = "ready"

        return {
            "session_id": session_id,
            "company_name": company_name,
            "stock_code": stock_code,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"Parse failed for session {session_id}: {e}", exc_info=True)
        task["agent_status"]["parse"] = "failed"
        task["agent_status"]["parse_error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/agents/{agent_name}")
async def run_agent(session_id: int, agent_name: str) -> dict[str, Any]:
    """步骤2：单独运行一个分析师 agent"""
    if agent_name not in ANALYST_AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid analyst agent: {agent_name}")

    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    task = next((t for t in TASKS.values() if t["session_id"] == session_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for session")

    current_status = task["agent_status"].get(agent_name)
    if current_status not in ("ready", "failed"):
        # 允许重新运行已失败的 agent，其他状态拒绝
        raise HTTPException(
            status_code=409,
            detail=f"Agent {agent_name} is {current_status}, cannot run now",
        )

    # 检查 parse 是否完成
    if task["agent_status"].get("parse") != "completed":
        raise HTTPException(status_code=409, detail="必须先完成解析才能运行分析师")

    # 标记为 running 并异步执行
    task["agent_status"][agent_name] = "running"
    store.update_session_status(session_id, "running")

    asyncio.create_task(_run_single_agent(session_id, agent_name, task["task_id"]))

    return {"session_id": session_id, "agent_name": agent_name, "status": "running"}


@app.post("/api/sessions/{session_id}/summarize")
async def run_summary_agent(session_id: int) -> dict[str, Any]:
    """步骤3：运行综合报告（要求所有分析师完成）"""
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    task = next((t for t in TASKS.values() if t["session_id"] == session_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for session")

    # 检查所有分析师是否完成
    incomplete = [a for a in ANALYST_AGENTS if task["agent_status"].get(a) != "completed"]
    if incomplete:
        raise HTTPException(
            status_code=409,
            detail=f"以下分析师尚未完成: {', '.join(incomplete)}",
        )

    current = task["agent_status"].get("summary_agent")
    if current == "running":
        raise HTTPException(status_code=409, detail="综合报告正在生成中")

    task["status"] = "running"
    task["agent_status"]["summary_agent"] = "running"
    store.update_session_status(session_id, "running")

    asyncio.create_task(_run_summary(session_id, task["task_id"]))

    return {"session_id": session_id, "status": "running"}


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str) -> dict[str, Any]:
    task = TASKS.get(task_id)
    if not task:
        return {"task_id": task_id, "status": "expired", "error": "Task expired or server restarted"}
    return task


@app.get("/api/sessions/{session_id}")
def get_session(session_id: int) -> dict[str, Any]:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/api/sessions/{session_id}/agents")
def get_agent_results(session_id: int) -> list[dict[str, Any]]:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return store.get_agent_results(session_id)


@app.get("/api/sessions/{session_id}/report")
def get_report(session_id: int) -> dict[str, Any]:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    report = store.get_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: int) -> list[dict[str, Any]]:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return store.get_chat_messages(session_id)


@app.post("/api/sessions/{session_id}/chat")
async def add_chat_message(session_id: int, payload: CreateChatRequest) -> dict[str, Any]:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.role != "user":
        message_id = store.add_chat_message(
            ChatMessageRecord(session_id=session_id, role=payload.role, content=payload.content)
        )
        return {"message_id": message_id, "status": "stored"}
    try:
        result = await chat_with_session_context(store, session_id, payload.content, payload.rag_mode)
        return {"status": "completed", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
