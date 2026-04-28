from __future__ import annotations

import json
import math
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover - optional dependency
    HuggingFaceEmbeddings = None

try:
    from langchain_community.vectorstores import FAISS as LangChainFAISS
except ImportError:  # pragma: no cover - optional dependency
    LangChainFAISS = None


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
    本地向量检索服务。

    当前实现优先使用 FAISS 作为实际向量索引，并把文档元数据单独保存在 JSON 清单中。
    这样 JSON 只承担元数据持久化角色，不再作为“向量索引”本体。

    如果运行环境缺少 embedding 或 FAISS 依赖，则回退为基于词频余弦相似度的轻量检索，
    以保证开发环境和单测仍可运行。
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

        base_path = self.store_path if not self.store_path.suffix else self.store_path.with_suffix("")
        self.index_dir = base_path.parent / f"{base_path.name}_faiss"
        self.docs_path = base_path.parent / f"{base_path.name}_docs.json"

    def _load_rows(self) -> list[dict[str, Any]]:
        if self.docs_path.exists():
            with open(self.docs_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # 兼容旧版：历史上直接把文档列表写进 store_path 指向的 JSON 文件
        if self.store_path.suffix == ".json" and self.store_path.exists():
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []

        return []

    def _save_rows(self, rows: list[dict[str, Any]]) -> None:
        with open(self.docs_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def list_documents(self) -> list[dict[str, Any]]:
        return self._load_rows()

    def _get_embeddings(self):
        if HuggingFaceEmbeddings is None:
            return None
        if self._embedding_client is None:
            self._embedding_client = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        return self._embedding_client

    def _load_faiss_store(self):
        embeddings_client = self._get_embeddings()
        if embeddings_client is None or LangChainFAISS is None or not self.index_dir.exists():
            return None
        try:
            return LangChainFAISS.load_local(
                str(self.index_dir),
                embeddings_client,
                allow_dangerous_deserialization=True,
            )
        except Exception:
            return None

    def _rebuild_faiss_index(self, rows: list[dict[str, Any]]) -> bool:
        embeddings_client = self._get_embeddings()
        if embeddings_client is None or LangChainFAISS is None:
            return False

        shutil.rmtree(self.index_dir, ignore_errors=True)
        if not rows:
            return False

        texts = [row.get("content", "") for row in rows]
        metadatas = [
            {
                "doc_id": row.get("doc_id"),
                "session_id": row.get("session_id"),
                "stock_code": row.get("stock_code"),
                "company_name": row.get("company_name"),
                "title": row.get("title"),
                "metadata": row.get("metadata", {}),
                "doc_type": row.get("doc_type"),
            }
            for row in rows
        ]

        store = LangChainFAISS.from_texts(texts, embeddings_client, metadatas=metadatas)
        store.save_local(str(self.index_dir))
        return True

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

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(row.get("metadata") or {})
        doc_type = row.get("doc_type") or metadata.get("type")
        return {
            "doc_id": row.get("doc_id"),
            "session_id": row.get("session_id", -1),
            "stock_code": row.get("stock_code"),
            "company_name": row.get("company_name"),
            "title": row.get("title", "未命名文档"),
            "content": row.get("content", ""),
            "metadata": metadata,
            "doc_type": doc_type,
        }

    @staticmethod
    def _result_from_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "doc_id": row.get("doc_id"),
            "session_id": row.get("session_id"),
            "stock_code": row.get("stock_code"),
            "company_name": row.get("company_name"),
            "title": row.get("title"),
            "content": row.get("content"),
            "metadata": row.get("metadata", {}),
        }

    def replace_documents(self, rows: list[dict[str, Any]]) -> int:
        normalized_rows = [self._normalize_row(row) for row in rows]
        self._save_rows(normalized_rows)
        self._rebuild_faiss_index(normalized_rows)
        return len(normalized_rows)

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
        for idx, (title, content) in enumerate(chunks):
            row = self._normalize_row(
                {
                    "doc_id": f"{session_id}:{idx}",
                    "session_id": session_id,
                    "stock_code": stock_code,
                    "company_name": company_name,
                    "title": title,
                    "content": content,
                    "metadata": metadata,
                }
            )
            rows.append(row)

        self._save_rows(rows)
        self._rebuild_faiss_index(rows)
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        stock_code: str | None = None,
        top_k: int = 4,
    ) -> list[dict[str, Any]]:
        rows = self._load_rows()
        search_rows = rows if stock_code is None else [row for row in rows if row.get("stock_code") == stock_code]
        if not search_rows:
            return []

        faiss_store = self._load_faiss_store()
        if faiss_store is None and rows:
            self._rebuild_faiss_index(rows)
            faiss_store = self._load_faiss_store()

        if faiss_store is not None:
            fetch_k = max(top_k * 8, len(rows))
            try:
                docs_and_scores = faiss_store.similarity_search_with_score(query, k=min(fetch_k, len(rows)))
            except Exception:
                docs_and_scores = []

            faiss_results: list[dict[str, Any]] = []
            seen_doc_ids: set[str] = set()
            for doc, _score in docs_and_scores:
                meta = dict(doc.metadata or {})
                if stock_code and meta.get("stock_code") != stock_code:
                    continue
                doc_id = str(meta.get("doc_id") or "")
                if doc_id and doc_id in seen_doc_ids:
                    continue
                seen_doc_ids.add(doc_id)
                faiss_results.append(
                    {
                        "doc_id": meta.get("doc_id"),
                        "session_id": meta.get("session_id"),
                        "stock_code": meta.get("stock_code"),
                        "company_name": meta.get("company_name"),
                        "title": meta.get("title"),
                        "content": doc.page_content,
                        "metadata": meta.get("metadata", {}),
                    }
                )
                if len(faiss_results) >= top_k:
                    return faiss_results

        query_counter = self._counter_embedding(query)
        ranked = sorted(
            search_rows,
            key=lambda row: self._cosine_similarity(
                query_counter, self._counter_embedding(f"{row.get('title', '')}\n{row.get('content', '')}")
            ),
            reverse=True,
        )
        return [self._result_from_row(row) for row in ranked[:top_k]]
