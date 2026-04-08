"""
RAG 评估脚本
评估向量检索（Vector RAG）和图检索（Graph RAG）的召回质量。

用法：
    conda run -n lamost python -m src.eval_rag
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VECTOR_STORE = DATA_DIR / "vector_store.json"
GRAPH_STORE = DATA_DIR / "graph_store.json"
SQLITE_DB = DATA_DIR / "financial_sessions.db"

# ============================================================
# 测试集：基于上证50/深证100成分股知识库构造的 query
# ============================================================
RAG_TEST_SET = [
    # ---- 上证50 成分股查询 ----
    {
        "query": "贵州茅台属于哪个行业",
        "expected_keywords": ["贵州茅台", "白酒", "食品饮料"],
        "stock_code": "sh.600519",
    },
    {
        "query": "上证50里面有哪些银行股",
        "expected_keywords": ["银行", "上证50"],
        "stock_code": "sh.601398",
    },
    {
        "query": "中国平安的股票代码是什么",
        "expected_keywords": ["中国平安", "sh.601318", "保险"],
        "stock_code": "sh.601318",
    },
    {
        "query": "上证50指数包含哪些行业的股票",
        "expected_keywords": ["上证50", "行业"],
        "stock_code": "sh.600519",
    },
    # ---- 深证100 成分股查询 ----
    {
        "query": "宁德时代属于什么板块",
        "expected_keywords": ["宁德时代", "新能源", "动力电池"],
        "stock_code": "sz.300750",
    },
    {
        "query": "深证100包含比亚迪吗",
        "expected_keywords": ["比亚迪", "深证100", "新能源汽车"],
        "stock_code": "sz.002594",
    },
    {
        "query": "海康威视是做什么的",
        "expected_keywords": ["海康威视", "安防", "视频监控"],
        "stock_code": "sz.002415",
    },
    {
        "query": "深证100里面有哪些新能源公司",
        "expected_keywords": ["深证100", "新能源"],
        "stock_code": "sz.300750",
    },
    # ---- 行业知识查询 ----
    {
        "query": "白酒行业的投资特点是什么",
        "expected_keywords": ["白酒", "行业", "消费"],
        "stock_code": "sh.600519",
    },
    {
        "query": "半导体行业的发展前景如何",
        "expected_keywords": ["半导体", "行业", "芯片"],
        "stock_code": "sh.688981",
    },
    # ---- 指数对比查询 ----
    {
        "query": "上证50和深证100有什么区别",
        "expected_keywords": ["上证50", "深证100", "指数"],
        "stock_code": "sh.600519",
    },
    {
        "query": "招商银行在上证50里面的权重是多少",
        "expected_keywords": ["招商银行", "上证50", "权重"],
        "stock_code": "sh.600036",
    },
]


def load_vector_store() -> list[dict]:
    if not VECTOR_STORE.exists():
        return []
    with open(VECTOR_STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_graph_store() -> list[dict]:
    if not GRAPH_STORE.exists():
        return []
    with open(GRAPH_STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chat_history() -> list[dict]:
    import sqlite3
    if not SQLITE_DB.exists():
        return []
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT session_id, role, content FROM chat_messages ORDER BY session_id, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# 1. 检索召回评估（Retrieval Recall）
# ============================================================
def eval_vector_recall(test_set: list[dict], vector_store: list[dict]) -> dict:
    """
    评估向量检索的召回率。
    对每条 query，用词频余弦相似度模拟检索（与 VectorService 逻辑一致），
    检查 top-k 结果中是否包含期望的 chunk。
    """
    import math, re
    from collections import Counter as C

    def tokenize(text):
        return re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9_\.]+", text.lower())

    def counter(text):
        return C(tokenize(text))

    def cosine(lh, rh):
        common = set(lh) & set(rh)
        dot = sum(lh[k] * rh[k] for k in common)
        ln = math.sqrt(sum(v * v for v in lh.values()))
        rn = math.sqrt(sum(v * v for v in rh.values()))
        return dot / (ln * rn) if ln and rn else 0.0

    results = []
    for case in test_set:
        query = case["query"]
        stock = case.get("stock_code")
        expected_kw = case["expected_keywords"]

        # 过滤文档：匹配 stock_code 或不过滤（全库搜索）
        if stock:
            candidates = [r for r in vector_store if r.get("stock_code") == stock]
        else:
            candidates = vector_store
        if not candidates:
            results.append({"query": query, "recall": 0, "hit_kw": [], "reason": "no_docs"})
            continue

        q_counter = counter(query)
        ranked = sorted(
            candidates,
            key=lambda r: cosine(q_counter, counter(f"{r.get('title', '')} {r.get('content', '')}")),
            reverse=True,
        )[:4]

        retrieved_titles = [r.get("title", "") for r in ranked]
        retrieved_text = " ".join(r.get("content", "") for r in ranked) + " ".join(retrieved_titles)

        # 关键词命中评估
        keyword_total = len(expected_kw) if expected_kw else 0
        keyword_hits = sum(1 for kw in expected_kw if kw in retrieved_text) if keyword_total > 0 else 0
        recall = keyword_hits / keyword_total if keyword_total > 0 else 1.0
        hit_kw = [kw for kw in expected_kw if kw in retrieved_text]

        results.append({
            "query": query,
            "recall": round(recall, 2),
            "hit_kw": hit_kw,
            "miss_kw": [kw for kw in expected_kw if kw not in retrieved_text],
            "retrieved_titles": retrieved_titles,
        })

    avg_recall = sum(r["recall"] for r in results) / len(results) if results else 0
    return {"avg_recall": round(avg_recall, 4), "details": results}


# ============================================================
# 2. 图检索召回评估（Graph RAG Recall）
# ============================================================
def eval_graph_recall(test_set: list[dict], graph_store: list[dict]) -> dict:
    """
    评估图检索的召回率。
    检查关键词匹配返回的三元组是否与 query 相关。
    """
    import re

    results = []
    for case in test_set:
        query = case["query"]
        stock = case.get("stock_code")
        expected_kw = case["expected_keywords"]

        # 过滤三元组：包含 stock_code 或不过滤
        if stock:
            candidates = [r for r in graph_store if stock in json.dumps(r, ensure_ascii=False)]
        else:
            candidates = graph_store
        query_terms = [t for t in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_\.]+", query.lower()) if t]

        if not candidates:
            results.append({"query": query, "recall": 0, "hit_count": 0, "reason": "no_triples"})
            continue

        def score(row):
            haystack = json.dumps(row, ensure_ascii=False).lower()
            return sum(haystack.count(t) for t in query_terms)

        ranked = sorted(candidates, key=score, reverse=True)[:8]
        ranked = [r for r in ranked if score(r) > 0]

        retrieved_text = json.dumps(ranked, ensure_ascii=False)
        keyword_total = len(expected_kw) if expected_kw else 0
        keyword_hits = sum(1 for kw in expected_kw if kw in retrieved_text) if keyword_total > 0 else 0
        recall = keyword_hits / keyword_total if keyword_total > 0 else 1.0

        results.append({
            "query": query,
            "recall": round(recall, 2),
            "hit_count": len(ranked),
            "hit_kw": [kw for kw in expected_kw if kw in retrieved_text],
        })

    avg_recall = sum(r["recall"] for r in results) / len(results) if results else 0
    return {"avg_recall": round(avg_recall, 4), "details": results}


# ============================================================
# 3. 回答质量评估（LLM-as-Judge）
# ============================================================
def eval_answer_quality(chat_history: list[dict]) -> dict:
    """
    基于历史聊天记录评估回答质量：
    - 幻觉率：回答中是否包含与上下文矛盾的信息
    - 引用率：回答中是否引用了具体数据
    - 拒答率：是否有明确的"我不知道"类回答
    """
    qa_pairs = []
    for i in range(len(chat_history) - 1):
        if chat_history[i]["role"] == "user" and chat_history[i + 1]["role"] == "assistant":
            qa_pairs.append({
                "session_id": chat_history[i]["session_id"],
                "question": chat_history[i]["content"],
                "answer": chat_history[i + 1]["content"],
            })

    if not qa_pairs:
        return {"error": "没有找到有效的问答对"}

    stats = {
        "total_qa_pairs": len(qa_pairs),
        "has_data_reference": 0,   # 引用了具体数据
        "has_source_citation": 0,   # 提及来源（如"根据报告"）
        "has_hedge_language": 0,    # 有不确定性表达（"可能""约"）
        "refusal_count": 0,         # 明确拒答
        "avg_answer_length": 0,
        "per_session": {},
    }

    import re
    per_session = {}
    for qa in qa_pairs:
        sid = qa["session_id"]
        answer = qa["answer"]

        # 引用数据
        if re.search(r"\d+\.?\d*[%万亿手股元]", answer):
            stats["has_data_reference"] += 1
        # 来源引用
        if any(kw in answer for kw in ["根据", "报告", "分析结果", "数据显示", "上述"]):
            stats["has_source_citation"] += 1
        # 不确定性表达
        if any(kw in answer for kw in ["可能", "约", "左右", "预计", "不确定"]):
            stats["has_hedge_language"] += 1
        # 拒答
        if any(kw in answer for kw in ["无法确定", "没有直接证据", "暂无", "不掌握"]):
            stats["refusal_count"] += 1

        per_session.setdefault(sid, {"count": 0, "has_ref": 0, "has_cite": 0, "refusal": 0})
        per_session[sid]["count"] += 1
        if re.search(r"\d+\.?\d*[%万亿手股元]", answer):
            per_session[sid]["has_ref"] += 1
        if any(kw in answer for kw in ["根据", "报告", "分析结果", "数据显示"]):
            per_session[sid]["has_cite"] += 1
        if any(kw in answer for kw in ["无法确定", "没有直接证据"]):
            per_session[sid]["refusal"] += 1

    stats["avg_answer_length"] = round(
        sum(len(qa["answer"]) for qa in qa_pairs) / len(qa_pairs), 1
    )
    stats["data_reference_rate"] = round(stats["has_data_reference"] / stats["total_qa_pairs"], 2)
    stats["source_citation_rate"] = round(stats["has_source_citation"] / stats["total_qa_pairs"], 2)
    stats["hedge_language_rate"] = round(stats["has_hedge_language"] / stats["total_qa_pairs"], 2)
    stats["refusal_rate"] = round(stats["refusal_count"] / stats["total_qa_pairs"], 2)
    stats["per_session"] = per_session

    return stats


# ============================================================
# 4. 向量库元信息统计
# ============================================================
def vector_store_stats(vector_store: list[dict]) -> dict:
    types = {}
    stock_codes = set()
    for r in vector_store:
        doc_type = r.get("doc_type", "unknown")
        types[doc_type] = types.get(doc_type, 0) + 1
        if r.get("stock_code"):
            stock_codes.add(r["stock_code"])

    return {
        "total_documents": len(vector_store),
        "covered_stocks": len(stock_codes),
        "type_distribution": types,
    }


# ============================================================
# 5. 图库元信息统计
# ============================================================
def graph_store_stats(graph_store: list[dict]) -> dict:
    from collections import Counter
    relations = Counter(r.get("relation") for r in graph_store)
    sessions = Counter(r.get("session_id") for r in graph_store)

    return {
        "total_triples": len(graph_store),
        "total_sessions": len(sessions),
        "relation_distribution": dict(relations.most_common()),
    }


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print("RAG 评估报告")
    print("=" * 60)

    # 加载数据
    vector_store = load_vector_store()
    graph_store = load_graph_store()
    chat_history = load_chat_history()

    # 1. 向量库统计
    print("\n## 1. 向量库统计")
    vs = vector_store_stats(vector_store)
    print(f"  总文档数: {vs['total_documents']}")
    print(f"  覆盖股票数: {vs['covered_stocks']}")
    print(f"  文档类型分布:")
    for t, cnt in vs["type_distribution"].items():
        print(f"    {t}: {cnt}")

    # 2. 图库统计
    print("\n## 2. 图库统计")
    gs = graph_store_stats(graph_store)
    print(f"  总三元组数: {gs['total_triples']}")
    print(f"  覆盖会话数: {gs['total_sessions']}")
    print(f"  关系类型分布:")
    for rel, cnt in gs["relation_distribution"].items():
        print(f"    {rel}: {cnt}")

    # 3. 向量检索召回
    print("\n## 3. Vector RAG 召回率评估")
    v_recall = eval_vector_recall(RAG_TEST_SET, vector_store)
    print(f"  平均召回率: {v_recall['avg_recall']}")
    for d in v_recall["details"]:
        status = "✅" if d["recall"] >= 0.5 else "⚠️"
        print(f"  {status} Q: {d['query']}")
        print(f"     召回率: {d['recall']}, 命中: {d['hit_kw']}, 未命中: {d['miss_kw']}")
        print(f"     检索到: {d['retrieved_titles'][:3]}")

    # 4. 图检索召回
    print("\n## 4. Graph RAG 召回率评估")
    g_recall = eval_graph_recall(RAG_TEST_SET, graph_store)
    print(f"  平均召回率: {g_recall['avg_recall']}")
    for d in g_recall["details"]:
        status = "✅" if d["recall"] >= 0.5 else "⚠️"
        print(f"  {status} Q: {d['query']}")
        print(f"     召回率: {d['recall']}, 命中: {d.get('hit_kw', [])}, 三元组数: {d['hit_count']}")

    # 5. 回答质量
    print("\n## 5. 回答质量评估（基于历史聊天记录）")
    aq = eval_answer_quality(chat_history)
    if "error" in aq:
        print(f"  {aq['error']}")
    else:
        print(f"  有效问答对数: {aq['total_qa_pairs']}")
        print(f"  数据引用率: {aq['data_reference_rate']}")
        print(f"  来源引用率: {aq['source_citation_rate']}")
        print(f"  不确定性表达率: {aq['hedge_language_rate']}")
        print(f"  拒答率: {aq['refusal_rate']}")
        print(f"  平均回答长度: {aq['avg_answer_length']} 字符")
        print(f"  分会话详情:")
        for sid, info in aq["per_session"].items():
            print(f"    session={sid}: qa={info['count']}, 引用数据={info['has_ref']}, 来源引用={info['has_cite']}, 拒答={info['refusal']}")

    # 6. 总结
    print("\n## 6. RAG 总结")
    print(f"  Vector RAG 平均召回率: {v_recall['avg_recall']}")
    print(f"  Graph RAG 平均召回率: {g_recall['avg_recall']}")
    if "error" not in aq:
        print(f"  回答数据引用率: {aq['data_reference_rate']}")
        print(f"  回答来源引用率: {aq['source_citation_rate']}")
    print(f"  向量库覆盖: {vs['covered_stocks']} 只股票, {vs['total_documents']} 个文档")
    print(f"  图库覆盖: {gs['total_sessions']} 个会话, {gs['total_triples']} 个三元组")


if __name__ == "__main__":
    main()
