# Financial MCP Agent — 金融多智能体研究工作台

## 项目简介

基于 Multi-Agent 架构的 A 股智能研究平台，用户输入自然语言查询后，系统自动调度多个专业 Agent 并行完成多维度分析，汇总生成结构化投资研究报告，并支持 RAG 对话追问。

## 技术栈

Python / FastAPI / LangGraph / LangChain / Pydantic / vLLM / MCP 协议 / SQLite / Neo4j

## STAR 法则

**S — 背景**：A 股全面分析需查阅财报、K 线、新闻等多源数据，人工耗时且易遗漏，缺乏自动化多维度分析工具。

**T — 任务**：设计端到端 Multi-Agent 金融分析系统，实现自然语言查询→多维度并行分析→结构化报告→RAG 追问的完整流程。

**A — 行动**：
- 基于 LangGraph 构建 5 个专业 Agent（基本面/技术面/估值/新闻/汇总），采用 ReAct 框架自主决策工具调用
- 设计 Pydantic AgentState 状态模型，实现多 Agent 间结构化数据的增量共享
- 异步调度引擎支持按需执行单 Agent，带超时保护，单点失败不影响全局
- 自研 A 股 MCP Server 封装 20+ 金融数据工具，工具白名单限定各 Agent 可访问范围
- 多策略实体抽取（正则 + LLM + 搜索 API）确保股票识别率
- SQLite 持久化 + Neo4j 图存储（自动降级）+ 本地向量检索，支撑 RAG 问答

**R — 结果**：
- 实现自然语言→结构化报告的端到端流程，4 维度并行分析 + 自动汇总
- 分步执行架构鲁棒性强，本地 vLLM 部署保障数据隐私
