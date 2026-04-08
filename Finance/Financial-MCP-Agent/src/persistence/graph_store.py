from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langchain_community.graphs import Neo4jGraph


class GraphStore:
    """
    轻量级图存储实现。
    支持本地 JSON 存储（开发环境）和 Neo4j 图数据库（生产环境）。
    """

    def __init__(self, store_path: str | Path):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        # 尝试连接 Neo4j
        self.neo4j_uri = os.environ.get("NEO4J_URI")
        self.neo4j_user = os.environ.get("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.environ.get("NEO4J_PASSWORD")

        self.use_neo4j = False
        if self.neo4j_uri and self.neo4j_password:
            try:
                self.graph = Neo4jGraph(
                    url=self.neo4j_uri,
                    username=self.neo4j_user,
                    password=self.neo4j_password,
                    refresh_schema=False,
                )
                self.use_neo4j = True
                print(f"Connected to Neo4j at {self.neo4j_uri}")
            except Exception as e:
                print(f"Failed to connect to Neo4j, fallback to JSON: {e}")

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        with open(self.store_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_rows(self, rows: list[dict[str, Any]]) -> None:
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def index_report(
        self,
        session_id: int,
        stock_code: str | None,
        company_name: str | None,
        report_text: str,
    ) -> int:
        triples = []
        entity_label = company_name or stock_code or f"session_{session_id}"
        
        # 1. 基础关系：股票代码
        if company_name and stock_code:
            triples.append({
                "source": company_name,
                "relation": "股票代码",
                "target": stock_code,
                "type": "Company"
            })

        # 2. 从文本中提取关键指标和风险（简易启发式提取）
        for line in report_text.splitlines():
            normalized = line.strip().lstrip("#*- ")
            if not normalized:
                continue
            
            rel = None
            if "风险" in normalized:
                rel = "风险提示"
            elif any(keyword in normalized for keyword in ["行业", "赛道", "产业链"]):
                rel = "行业关联"
            elif re.search(r"(毛利率|ROE|市盈率|PE|PB|MACD|RSI)", normalized, re.IGNORECASE):
                rel = "指标观察"

            if rel:
                triples.append({
                    "source": entity_label,
                    "relation": rel,
                    "target": normalized[:160],
                    "type": "Company"
                })

        if not triples:
            return 0

        # 3. 存储
        if self.use_neo4j:
            # Neo4j 异步写入（简化版同步实现）
            for t in triples:
                query = (
                    "MERGE (s:Entity {name: $source}) "
                    "MERGE (o:Entity {name: $target}) "
                    f"MERGE (s)-[r:`{t['relation']}`]->(o) "
                    "SET r.session_id = $session_id, r.stock_code = $stock_code"
                )
                self.graph.query(
                    query,
                    {
                        "source": t["source"],
                        "target": t["target"],
                        "session_id": session_id,
                        "stock_code": stock_code,
                    },
                )
        else:
            # JSON 回退
            rows = self._load_rows()
            # 清理旧 session 数据实现更新
            rows = [row for row in rows if row.get("session_id") != session_id]
            for t in triples:
                t.update({"session_id": session_id, "stock_code": stock_code, "company_name": company_name})
            rows.extend(triples)
            self._save_rows(rows)

        return len(triples)

    def query_related(
        self,
        query: str,
        stock_code: str | None = None,
        company_name: str | None = None,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        if self.use_neo4j:
            # Neo4j 查询：查找与关键词相关的实体及其周围的关系
            # 这里实现一个简单的关键词模糊匹配查询
            cypher = (
                "MATCH (s:Entity)-[r]->(o:Entity) "
                "WHERE s.name CONTAINS $q OR o.name CONTAINS $q OR type(r) CONTAINS $q "
                "RETURN s.name as source, type(r) as relation, o.name as target "
                "LIMIT $top_k"
            )
            result = self.graph.query(cypher, {"q": query[:20], "top_k": top_k})
            return result

        # JSON 模式原有逻辑
        rows = self._load_rows()
        if stock_code:
            rows = [row for row in rows if stock_code in json.dumps(row, ensure_ascii=False)]
        if company_name:
            rows = [row for row in rows if company_name in json.dumps(row, ensure_ascii=False)] or rows

        query_terms = [term for term in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_\.]+", query.lower()) if term]

        def score(row: dict[str, Any]) -> int:
            haystack = json.dumps(row, ensure_ascii=False).lower()
            return sum(haystack.count(term) for term in query_terms)

        ranked = sorted(rows, key=score, reverse=True)
        return [row for row in ranked[:top_k] if score(row) > 0]
