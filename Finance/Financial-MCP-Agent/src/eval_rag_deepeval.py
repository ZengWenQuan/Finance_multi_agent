"""
DeepEval RAG 评估脚本

使用 DeepEval 框架评估 RAG 系统的核心指标：
- Context Precision  (上下文精确率)
- Context Recall     (上下文召回率)
- Answer Relevancy  (回答相关性)
- Faithfulness       (回答忠实度)

流程：
  测试 query → 真实 VectorService / GraphStore 检索 → 真实 LLM 生成回答 → DeepEval 评估

用法：
    # 离线模式（纯关键词，不需要 LLM API）
    conda run -n lamost python -m src.eval_rag_deepeval --mode offline

    # DeepEval 完整评估（需要 LLM API，会调 2 次：1次生成回答 + 1次评估）
    conda run -n lamost python -m src.eval_rag_deepeval --mode vector
    conda run -n lamost python -m src.eval_rag_deepeval --mode graph
    conda run -n lamost python -m src.eval_rag_deepeval --mode hybrid

    # 只跑前 N 条（调试用）
    conda run -n lamost python -m src.eval_rag_deepeval --mode vector --sample 2
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI
from deepeval.models.base_model import DeepEvalBaseLLM

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VECTOR_STORE = DATA_DIR / "vector_store"
GRAPH_STORE = DATA_DIR / "graph_store.json"

# ============================================================
# LLM 配置（DeepEval 需要调用 LLM 来评估）
# ============================================================
def _get_llm_config():
    """从 .env 读取 LLM 配置，供 DeepEval 使用"""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
    return {
        "model": os.getenv("OPENAI_COMPATIBLE_MODEL", "deepseek-chat"),
        "api_key": os.getenv("OPENAI_COMPATIBLE_API_KEY", ""),
        "base_url": os.getenv("OPENAI_COMPATIBLE_BASE_URL", "https://api.deepseek.com/v1"),
    }


class DeepSeekModel(DeepEvalBaseLLM):
    """DeepEval 自定义模型：适配 DeepSeek OpenAI-compatible API"""

    def __init__(self):
        cfg = _get_llm_config()
        self._model = cfg["model"]
        self._client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )

    def generate(self, prompt: str) -> str:
        from openai import OpenAI
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=_get_llm_config()["api_key"],
            base_url=_get_llm_config()["base_url"],
        )
        response = await client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content

    def get_model_name(self) -> str:
        return self._model

    def load_model(self):
        """DeepEval 要求的抽象方法，我们用 OpenAI client 无需加载"""
        pass


# ============================================================
# 加载数据
# ============================================================
def load_vector_store() -> list[dict]:
    from src.services.vector_service import VectorService

    return VectorService(store_path=str(VECTOR_STORE)).list_documents()


def load_graph_store() -> list[dict]:
    with open(GRAPH_STORE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 初始化真实 RAG 服务（与生产代码完全一致）
# ============================================================
def _init_services():
    """初始化 VectorService 和 GraphStore，与 backend.py 完全一致"""
    from src.services.vector_service import VectorService
    from src.persistence.graph_store import GraphStore

    vector_service = VectorService(store_path=str(VECTOR_STORE))
    graph_store = GraphStore(store_path=str(GRAPH_STORE))
    return vector_service, graph_store


# ============================================================
# 检索函数：直接调用真实服务
# ============================================================
def retrieve_context(query: str, stock_code: str | None = None, top_k: int = 4) -> list[str]:
    """调用真实 VectorService.similarity_search() 进行检索"""
    vector_service, _ = _init_services()
    hits = vector_service.similarity_search(query, stock_code=stock_code, top_k=top_k)
    return [
        f"[{hit.get('title', '')}] {hit.get('content', '')}"
        for hit in hits if hit.get("content")
    ]


def retrieve_graph_context(query: str, stock_code: str | None = None, top_k: int = 8) -> list[str]:
    """调用真实 GraphStore.query_related() 进行检索"""
    _, graph_store = _init_services()
    hits = graph_store.query_related(query, stock_code=stock_code, top_k=top_k)
    return [
        f"{item.get('source', '')} - {item.get('relation', '')} - {item.get('target', '')}"
        for item in hits
    ]


# ============================================================
# RAG 回答函数：与 chat_service.py 使用相同的 prompt 模式
# ============================================================
def generate_rag_answer(query: str, context: list[str]) -> str:
    """与 chat_service.py 的 RAG prompt 一致的回答生成"""
    from langchain_openai import ChatOpenAI

    cfg = _get_llm_config()
    llm = ChatOpenAI(
        model=cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        temperature=0.2,
        max_tokens=800,
    )

    context_str = "\n\n".join(context) if context else "暂无相关信息"
    # 与 chat_service.py 一致的 system prompt
    system_prompt = (
        "你是一个面向投研前端页面的聊天助理。\n\n"
        "你的职责：\n"
        "1. 基于参考上下文回答问题\n"
        "2. 优先引用上下文中的具体数据\n"
        "3. 如果上下文中没有答案，明确说明「当前会话结果中没有直接证据」\n"
        "4. 不要编造新的市场数据\n\n"
        f"检索增强上下文：\n{context_str}"
    )

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ])
    return response.content if hasattr(response, "content") else str(response)


# ============================================================
# 测试数据集：与手动评估一致，增加 ground_truth
# ============================================================
RAG_EVAL_DATA = [
    {
        "input": "贵州茅台属于哪个行业",
        "actual_output": "",  # 运行时由 LLM 生成
        "expected_output": "贵州茅台属于白酒行业（申万一级分类：食品饮料）",
        "retrieval_context": [],  # 运行时由检索函数填充
        "stock_code": "sh.600519",
    },
    {
        "input": "上证50里面有哪些银行股",
        "actual_output": "",
        "expected_output": "上证50中的银行股包括工商银行、建设银行、农业银行、招商银行、交通银行等",
        "retrieval_context": [],
        "stock_code": "sh.601398",
    },
    {
        "input": "中国平安的股票代码是什么",
        "actual_output": "",
        "expected_output": "中国平安的股票代码是 sh.601318，属于保险行业",
        "retrieval_context": [],
        "stock_code": "sh.601318",
    },
    {
        "input": "上证50指数包含哪些行业的股票",
        "actual_output": "",
        "expected_output": "上证50指数包含银行、非银金融、食品饮料、电子、电力设备新能源、医药生物等多个行业",
        "retrieval_context": [],
        "stock_code": "sh.600519",
    },
    {
        "input": "宁德时代属于什么板块",
        "actual_output": "",
        "expected_output": "宁德时代（sz.300750）属于电力设备行业，主营业务为动力电池，是深证100成分股",
        "retrieval_context": [],
        "stock_code": "sz.300750",
    },
    {
        "input": "深证100包含比亚迪吗",
        "actual_output": "",
        "expected_output": "是的，比亚迪（sz.002594）是深证100指数成分股，属于汽车行业（新能源汽车）",
        "retrieval_context": [],
        "stock_code": "sz.002594",
    },
    {
        "input": "海康威视是做什么的",
        "actual_output": "",
        "expected_output": "海康威视（sz.002415）属于计算机行业，主营安防监控设备，是深证100成分股",
        "retrieval_context": [],
        "stock_code": "sz.002415",
    },
    {
        "input": "深证100里面有哪些新能源公司",
        "actual_output": "",
        "expected_output": "深证100中的新能源相关公司包括宁德时代（动力电池）、比亚迪（新能源汽车）、隆基绿能（光伏）等",
        "retrieval_context": [],
        "stock_code": "sz.300750",
    },
    {
        "input": "白酒行业的投资特点是什么",
        "actual_output": "",
        "expected_output": "白酒行业属于消费品领域，具有高毛利率、强品牌壁垒、现金流好等特点，受消费升级和政策影响较大",
        "retrieval_context": [],
        "stock_code": "sh.600519",
    },
    {
        "input": "半导体行业的发展前景如何",
        "actual_output": "",
        "expected_output": "半导体行业具有高技术壁垒和周期性特征，受益于国产替代和AI需求增长，发展前景看好但短期波动较大",
        "retrieval_context": [],
        "stock_code": "sh.688981",
    },
    {
        "input": "上证50和深证100有什么区别",
        "actual_output": "",
        "expected_output": "上证50跟踪上海证券交易所前50大蓝筹股，侧重金融消费；深证100跟踪深圳证券交易所前100大股票，侧重科技成长",
        "retrieval_context": [],
        "stock_code": "sh.600519",
    },
    {
        "input": "招商银行在上证50里面的权重是多少",
        "actual_output": "",
        "expected_output": "招商银行（sh.600036）是上证50成分股，在上证50指数中有一定权重（具体权重随定期调整变化）",
        "retrieval_context": [],
        "stock_code": "sh.600036",
    },
]


# ============================================================
# DeepEval 评估
# ============================================================
def run_deepeval_evaluation(
    eval_data: list[dict],
    mode: str = "vector",  # "vector" or "graph" or "hybrid"
) -> None:
    """运行 DeepEval 的 4 项 RAG 评估指标"""
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        FaithfulnessMetric,
    )
    from deepeval.test_case import LLMTestCase

    cfg = _get_llm_config()
    custom_model = DeepSeekModel()

    test_cases = []

    for item in eval_data:
        query = item["input"]
        stock_code = item["stock_code"]

        # 检索
        if mode == "graph":
            retrieved = retrieve_graph_context(query, stock_code)
        elif mode == "hybrid":
            vector_ctx = retrieve_context(query, stock_code, top_k=3)
            graph_ctx = retrieve_graph_context(query, stock_code, top_k=5)
            retrieved = vector_ctx + graph_ctx
        else:
            retrieved = retrieve_context(query, stock_code, top_k=4)

        item["retrieval_context"] = retrieved

        # 生成回答（如果实际输出为空）
        if not item["actual_output"]:
            print(f"  生成回答: {query[:30]}...", end=" ", flush=True)
            answer = generate_rag_answer(query, retrieved)
            item["actual_output"] = answer
            print("完成")
        else:
            answer = item["actual_output"]

        tc = LLMTestCase(
            input=query,
            actual_output=answer,
            expected_output=item["expected_output"],
            retrieval_context=retrieved,
        )
        test_cases.append(tc)

    # 定义 4 个指标
    metrics = [
        ContextualPrecisionMetric(
            model=custom_model,
            threshold=0.5,
        ),
        ContextualRecallMetric(
            model=custom_model,
            threshold=0.5,
        ),
        AnswerRelevancyMetric(
            model=custom_model,
            threshold=0.5,
        ),
        FaithfulnessMetric(
            model=custom_model,
            threshold=0.5,
        ),
    ]

    print(f"\n开始 DeepEval 评估（mode={mode}，{len(test_cases)} 条测试用例）...")
    print(f"模型: {cfg['model']}")
    print(f"API: {cfg['base_url']}")
    print()

    evaluate(
        test_cases=test_cases,
        metrics=metrics,
    )


# ============================================================
# 简化版：不依赖 DeepEval LLM 的关键词召回评估（离线模式）
# ============================================================
def run_offline_evaluation(eval_data: list[dict]) -> dict:
    """离线评估：不需要 LLM，纯关键词命中"""
    results = []
    for item in eval_data:
        query = item["input"]
        stock_code = item["stock_code"]
        expected = item["expected_output"]

        # 检索
        retrieved = retrieve_context(query, stock_code, top_k=4)
        retrieved_text = " ".join(retrieved)

        # 关键词命中
        import re
        expected_terms = [t for t in re.findall(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9_\.]+", expected)]
        if not expected_terms:
            continue

        hits = sum(1 for t in expected_terms if t in retrieved_text)
        recall = hits / len(expected_terms) if expected_terms else 0

        results.append({
            "query": query,
            "recall": round(recall, 3),
            "hits": hits,
            "total_terms": len(expected_terms),
            "retrieved_count": len(retrieved),
        })

    return results


# ============================================================
# Main
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="DeepEval RAG 评估")
    parser.add_argument("--mode", choices=["vector", "graph", "hybrid", "offline"], default="offline",
                        help="评估模式：vector/graph/hybrid 使用 DeepEval LLM 评估；offline 纯关键词离线评估")
    parser.add_argument("--sample", type=int, default=0, help="仅评估前 N 条（0=全部）")
    args = parser.parse_args()

    print("=" * 60)
    print("DeepEval RAG 评估")
    print("=" * 60)

    # 统计知识库
    vector_store = load_vector_store()
    graph_store = load_graph_store()
    print(f"\n向量库: {len(vector_store)} 文档")
    print(f"图库: {len(graph_store)} 三元组")
    print(f"测试用例: {len(RAG_EVAL_DATA)} 条\n")

    eval_data = RAG_EVAL_DATA[:args.sample] if args.sample else RAG_EVAL_DATA

    if args.mode == "offline":
        # 离线模式：不需要 LLM API
        print("## 离线关键词召回评估\n")
        results = run_offline_evaluation(eval_data)

        for r in results:
            status = "OK" if r["recall"] >= 0.5 else "WARN"
            print(f"  [{status}] {r['query']}")
            print(f"       召回率={r['recall']:.1%}, 命中={r['hits']}/{r['total_terms']} 词, 检索={r['retrieved_count']} 篇")

        avg = sum(r["recall"] for r in results) / len(results) if results else 0
        print(f"\n  平均召回率: {avg:.1%}")

    else:
        # DeepEval LLM 评估模式
        run_deepeval_evaluation(eval_data, mode=args.mode)


if __name__ == "__main__":
    main()
