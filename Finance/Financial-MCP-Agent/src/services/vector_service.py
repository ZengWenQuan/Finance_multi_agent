from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover - optional dependency
    HuggingFaceEmbeddings = None


@dataclass
class VectorDocument:
    doc_id: str
    session_id: int
    stock_code: str | None
    company_name: str | None
    title: str
    content: str
    metadata: dict[str, Any]


class VectorService:
    """
    轻量级本地向量服务。

    优先使用 HuggingFaceEmbeddings；如果运行环境未安装对应依赖，
    则回退为基于词频余弦相似度的本地检索，保证功能和测试可运行。
    """

    def __init__(
        self,
        store_path: str | Path,
        embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model_name
        self._embedding_client = None

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        with open(self.store_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_rows(self, rows: list[dict[str, Any]]) -> None:
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def _get_embeddings(self):
        if HuggingFaceEmbeddings is None:
            return None
        if self._embedding_client is None:
            self._embedding_client = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        return self._embedding_client

    @staticmethod
    def _chunk_markdown(text: str) -> list[tuple[str, str]]:
        if not text.strip():
            return []

        chunks: list[tuple[str, str]] = []
        current_title = "全文"
        current_lines: list[str] = []

        for line in text.splitlines():
            if re.match(r"^\s{0,3}#{1,6}\s+", line):
                if current_lines:
                    chunks.append((current_title, "\n".join(current_lines).strip()))
                current_title = re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip() or "未命名章节"
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            chunks.append((current_title, "\n".join(current_lines).strip()))

        return [(title, content) for title, content in chunks if content.strip()]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9_\.]+", text.lower())

    @classmethod
    def _counter_embedding(cls, text: str) -> Counter:
        return Counter(cls._tokenize(text))

    @staticmethod
    def _cosine_similarity(lhs: Counter, rhs: Counter) -> float:
        common = set(lhs) & set(rhs)
        dot = sum(lhs[key] * rhs[key] for key in common)
        lhs_norm = math.sqrt(sum(value * value for value in lhs.values()))
        rhs_norm = math.sqrt(sum(value * value for value in rhs.values()))
        if lhs_norm == 0 or rhs_norm == 0:
            return 0.0
        return dot / (lhs_norm * rhs_norm)

    def index_report(
        self,
        session_id: int,
        stock_code: str | None,
        company_name: str | None,
        report_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        metadata = metadata or {}
        rows = self._load_rows()
        rows = [row for row in rows if row.get("session_id") != session_id]

        chunks = self._chunk_markdown(report_text) or [("全文", report_text)]
        embeddings_client = self._get_embeddings()
        chunk_texts = [content for _, content in chunks]
        dense_vectors = embeddings_client.embed_documents(chunk_texts) if embeddings_client else None

        for idx, (title, content) in enumerate(chunks):
            row = {
                "doc_id": f"{session_id}:{idx}",
                "session_id": session_id,
                "stock_code": stock_code,
                "company_name": company_name,
                "title": title,
                "content": content,
                "metadata": metadata,
            }
            if dense_vectors is not None:
                row["dense_vector"] = dense_vectors[idx]
            rows.append(row)

        self._save_rows(rows)
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        stock_code: str | None = None,
        top_k: int = 4,
    ) -> list[dict[str, Any]]:
        rows = self._load_rows()
        if stock_code:
            rows = [row for row in rows if row.get("stock_code") == stock_code]

        if not rows:
            return []

        embeddings_client = self._get_embeddings()
        if embeddings_client and all("dense_vector" in row for row in rows):
            query_vector = embeddings_client.embed_query(query)

            def dense_score(row: dict[str, Any]) -> float:
                vector = row.get("dense_vector") or []
                if not vector:
                    return 0.0
                dot = sum(float(a) * float(b) for a, b in zip(query_vector, vector))
                lhs_norm = math.sqrt(sum(float(a) * float(a) for a in query_vector))
                rhs_norm = math.sqrt(sum(float(a) * float(a) for a in vector))
                if lhs_norm == 0 or rhs_norm == 0:
                    return 0.0
                return dot / (lhs_norm * rhs_norm)

            ranked = sorted(rows, key=dense_score, reverse=True)
        else:
            query_counter = self._counter_embedding(query)
            ranked = sorted(
                rows,
                key=lambda row: self._cosine_similarity(
                    query_counter, self._counter_embedding(f"{row.get('title', '')}\n{row.get('content', '')}")
                ),
                reverse=True,
            )

        results = []
        for row in ranked[:top_k]:
            results.append(
                {
                    "doc_id": row["doc_id"],
                    "session_id": row["session_id"],
                    "stock_code": row.get("stock_code"),
                    "company_name": row.get("company_name"),
                    "title": row.get("title"),
                    "content": row.get("content"),
                    "metadata": row.get("metadata", {}),
                }
            )
        return results
