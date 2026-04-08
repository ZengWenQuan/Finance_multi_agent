from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.persistence.schemas import (
    AgentResultRecord,
    ChatMessageRecord,
    ReportRecord,
    SessionRecord,
)


class SQLiteSessionStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    company_name TEXT,
                    stock_code TEXT,
                    user_query TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'completed',
                    source TEXT NOT NULL DEFAULT 'cli',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    agent_name TEXT NOT NULL,
                    schema_version TEXT NOT NULL DEFAULT 'v1',
                    display_title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    structured_data_json TEXT NOT NULL DEFAULT '{}',
                    execution_trace_json TEXT NOT NULL DEFAULT '{}',
                    raw_context_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'completed',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(session_id, agent_name),
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL UNIQUE,
                    final_report TEXT NOT NULL,
                    report_path TEXT,
                    report_markdown_snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )

    @staticmethod
    def _dump_json(value: dict[str, Any]) -> str:
        return json.dumps(value or {}, ensure_ascii=False)

    @staticmethod
    def _load_json(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        return json.loads(value)

    def create_session(self, record: SessionRecord) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    session_name, company_name, stock_code, user_query,
                    status, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.session_name,
                    record.company_name,
                    record.stock_code,
                    record.user_query,
                    record.status,
                    record.source,
                    record.created_at,
                    record.updated_at,
                ),
            )
            return int(cursor.lastrowid)

    def update_session_status(self, session_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, session_id),
            )

    def update_session_details(
        self,
        session_id: int,
        session_name: str,
        company_name: str | None,
        stock_code: str | None,
        user_query: str,
        status: str,
        source: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET session_name = ?, company_name = ?, stock_code = ?, user_query = ?,
                    status = ?, source = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (session_name, company_name, stock_code, user_query, status, source, session_id),
            )

    def upsert_agent_result(self, record: AgentResultRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_results (
                    session_id, agent_name, schema_version, display_title, content,
                    structured_data_json, execution_trace_json, raw_context_json,
                    status, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, agent_name) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    display_title = excluded.display_title,
                    content = excluded.content,
                    structured_data_json = excluded.structured_data_json,
                    execution_trace_json = excluded.execution_trace_json,
                    raw_context_json = excluded.raw_context_json,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                (
                    record.session_id,
                    record.agent_name,
                    record.schema_version,
                    record.display_title,
                    record.content,
                    self._dump_json(record.structured_data_json),
                    self._dump_json(record.execution_trace_json),
                    self._dump_json(record.raw_context_json),
                    record.status,
                    record.error_message,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def upsert_report(self, record: ReportRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reports (
                    session_id, final_report, report_path, report_markdown_snapshot,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    final_report = excluded.final_report,
                    report_path = excluded.report_path,
                    report_markdown_snapshot = excluded.report_markdown_snapshot,
                    updated_at = excluded.updated_at
                """,
                (
                    record.session_id,
                    record.final_report,
                    record.report_path,
                    record.report_markdown_snapshot,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def add_chat_message(self, record: ChatMessageRecord) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (record.session_id, record.role, record.content, record.created_at),
            )
            return int(cursor.lastrowid)

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_name, company_name, stock_code, user_query,
                       status, source, created_at, updated_at
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, session_name, company_name, stock_code, user_query,
                       status, source, created_at, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_agent_results(self, session_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, agent_name, schema_version, display_title, content,
                       structured_data_json, execution_trace_json, raw_context_json,
                       status, error_message, created_at, updated_at
                FROM agent_results
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["structured_data_json"] = self._load_json(item["structured_data_json"])
            item["execution_trace_json"] = self._load_json(item["execution_trace_json"])
            item["raw_context_json"] = self._load_json(item["raw_context_json"])
            results.append(item)
        return results

    def get_report(self, session_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, session_id, final_report, report_path, report_markdown_snapshot,
                       created_at, updated_at
                FROM reports
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_chat_messages(self, session_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]
