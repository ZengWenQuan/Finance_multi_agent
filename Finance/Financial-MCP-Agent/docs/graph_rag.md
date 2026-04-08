# GraphRAG 详解：从基础到实现

## 1. 什么是 GraphRAG?

**GraphRAG (Graph Retrieval-Augmented Generation)** 是一种结合了 **知识图谱 (Knowledge Graph)** 和 **检索增强生成 (RAG)** 的高级技术。

传统的 Vector RAG（基于向量的检索）主要依赖文本分块（Chunks）的语义相似度。而 GraphRAG 引入了结构化的图数据，通过“点”和“边”来捕捉实体之间的复杂关系。

### 为什么需要 GraphRAG？
*   **全局视野**：传统 RAG 只能检索到局部的相似片段，难以回答“总结这家公司的所有风险”这种分散在文档各处的问题。
*   **多层级推理**：可以沿着图的路径进行多跳（Multi-hop）推理，例如：“A公司的竞争对手B最近有哪些利好消息？”
*   **语义连接**：通过图结构，即使两个实体在文本中相距甚远，也能建立逻辑关联。

---

## 2. 底层实现：知识图谱的存储

知识图谱主要由 **节点（Nodes）**、**关系（Edges）** 和 **属性（Properties）** 组成。

### 存储形式：LPG (Labeled Property Graph)
在专业的图数据库（如 Neo4j）中，数据以如下形式存储：

*   **节点 (Nodes)**：
    *   `ID`: `600519`
    *   `Label`: `Stock`
    *   `Properties`: `{name: "贵州茅台", industry: "白酒"}`
*   **关系 (Edges)**：
    *   `Source`: `贵州茅台`
    *   `Target`: `白酒行业`
    *   `Type`: `BELONGS_TO`
    *   `Properties`: `{weight: 0.9}`

### 示例数据结构
```json
(贵州茅台:Stock) -[:BELONGS_TO]-> (白酒:Industry)
(贵州茅台:Stock) -[:REPORTED_IN]-> (2024Q1财报:Report)
(2024Q1财报:Report) -[:HAS_RISK]-> ("原材料价格波动":Risk)
```

---

## 3. GraphRAG 的工作流程

### A. 索引阶段 (Indexing)
1.  **实体提取**：利用 LLM 提取文档中的实体（Entity）和关系（Relationship）。
2.  **社区发现 (Community Detection)**：对图进行聚类，识别出“密集区”（比如某个产业链的上下游）。
3.  **总结生成**：预先为每个社区生成摘要，存储在向量库中。

### B. 检索阶段 (Retrieval)
1.  **语义检索**：用户输入 Query，检索最相关的实体或社区（通过向量相似度）。
2.  **子图展开**：从这些起点出发，沿着边寻找关联的节点和属性。
3.  **上下文重构**：将图路径转化成文本形式，喂给 LLM。

---

## 4. 搜索示例

**用户提问：** “如果白酒行业原材料成本上涨，对茅台有什么影响？”

**GraphRAG 检索路径：**
1.  识别 Query 中的关键词：`白酒行业`、`原材料`、`茅台`。
2.  从图数据库中检索：
    *   `白酒行业` -[:INCLUDE]-> `贵州茅台`
    *   `贵州茅台` -[:RISK]-> `成本控制风险`
    *   `贵州茅台` -[:DEPENDS_ON]-> `原材料供应商X`
3.  **结果生成**：结合以上结构化信息，LLM 可以生成更精准的分析汇报，而不仅仅是堆砌相关的文本。

---

## 5. 项目中的实现路径

在本项目中，我们将 `GraphStore` 从本地 JSON 升级为 Neo4j：
1.  **存储层**：使用 `langchain_community.graphs.Neo4jGraph`。
2.  **逻辑层**：将提取的三元组直接写入 Neo4j 数据库。
3.  **检索层**：利用 Cypher 语言进行图遍历查询。
