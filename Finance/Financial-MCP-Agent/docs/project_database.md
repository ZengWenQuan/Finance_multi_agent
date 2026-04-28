# 项目数据库说明

## 结论

当前项目默认使用的是 **SQLite** 作为主业务数据库，文件路径为：

`Financial-MCP-Agent/data/financial_sessions.db`

这也是后端 `SQLiteSessionStore` 默认连接的数据库。

参考代码：

- [src/services/analysis_service.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/services/analysis_service.py:99)
- [src/persistence/sqlite_store.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/persistence/sqlite_store.py:16)

## 主数据库用途

`financial_sessions.db` 负责保存项目的核心业务数据，主要包括：

- `sessions`：一次分析会话的基础信息
- `agent_results`：各个分析 agent 的输出结果
- `reports`：综合报告
- `chat_messages`：会话聊天记录

建表逻辑定义在：

- [src/persistence/sqlite_store.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/persistence/sqlite_store.py:27)

## 主数据库表结构

当前主库包含 4 张核心表。

### `sessions`

用于保存一次分析会话的基础信息。

字段说明：

- `id`：主键，自增 session ID
- `session_name`：会话名称
- `company_name`：公司名称，可为空
- `stock_code`：股票代码，可为空
- `user_query`：用户原始问题
- `status`：会话状态，默认是 `completed`
- `source`：会话来源，默认是 `cli`
- `created_at`：创建时间
- `updated_at`：更新时间

### `agent_results`

用于保存各个分析 agent 的输出结果。

字段说明：

- `id`：主键，自增 ID
- `session_id`：关联 `sessions.id`
- `agent_name`：agent 名称，例如 `fundamental_agent`
- `schema_version`：结果结构版本，默认 `v1`
- `display_title`：前端展示标题
- `content`：agent 的文本输出
- `structured_data_json`：结构化结果 JSON
- `execution_trace_json`：执行轨迹 JSON
- `raw_context_json`：原始上下文 JSON
- `status`：执行状态，默认 `completed`
- `error_message`：错误信息
- `created_at`：创建时间
- `updated_at`：更新时间

约束说明：

- `UNIQUE(session_id, agent_name)`：同一个 session 下，同一个 agent 只保留一条记录

### `reports`

用于保存综合报告结果。

字段说明：

- `id`：主键，自增 ID
- `session_id`：关联 `sessions.id`，并且唯一
- `final_report`：最终报告正文
- `report_path`：报告文件路径，可为空
- `report_markdown_snapshot`：报告 Markdown 快照
- `created_at`：创建时间
- `updated_at`：更新时间

约束说明：

- `session_id UNIQUE`：一个 session 只对应一份综合报告

### `chat_messages`

用于保存聊天消息记录。

字段说明：

- `id`：主键，自增消息 ID
- `session_id`：关联 `sessions.id`
- `role`：消息角色，例如 `user` 或 `assistant`
- `content`：消息内容
- `created_at`：消息创建时间

## 表之间的关系

可以把这 4 张表理解成下面的关系：

- 一个 `session` 对应多条 `agent_results`
- 一个 `session` 对应一条 `report`
- 一个 `session` 对应多条 `chat_messages`

也就是说，`sessions` 是主表，其它三张表都围绕它展开。

## 默认数据文件位置

项目当前 `data` 目录下可以看到这些和存储相关的文件：

- `financial_sessions.db`：主业务数据库，当前实际在用
- `graph_store.json`：Graph RAG 的本地 JSON 回退存储
- `vector_store.json`：向量检索相关的历史/兼容数据文件
- `neo4j/`：Neo4j 相关目录
- `sessions.db`：存在，但默认代码没有把它作为主库使用

## RAG 相关存储和主数据库的区别

这个项目不只有一个“存储”概念，需要区分：

### 1. 主业务数据库

主业务数据库是 SQLite：

- 路径：`Financial-MCP-Agent/data/financial_sessions.db`
- 用途：保存 session、agent 结果、report、chat message

### 2. 向量检索存储

向量检索由 `VectorService` 管理：

- 默认路径来源：[src/services/analysis_service.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/services/analysis_service.py:108)
- 实现定义：[src/services/vector_service.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/services/vector_service.py:34)

代码设计上：

- 优先使用 `FAISS` 作为真实向量索引
- 文档元数据单独存为 JSON
- 如果缺少 embedding 或 FAISS 依赖，会回退到轻量检索

当前仓库里可见的是 `vector_store.json`，说明当前环境至少保留了 JSON 侧的数据。

### 3. Graph RAG 存储

Graph RAG 由 `GraphStore` 管理：

- 默认路径来源：[src/services/analysis_service.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/services/analysis_service.py:113)
- 实现定义：[src/persistence/graph_store.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/persistence/graph_store.py:12)

它支持两种模式：

- 默认/开发模式：写入 `graph_store.json`
- 生产可选模式：如果配置了 `NEO4J_URI` 和 `NEO4J_PASSWORD`，则连接 `Neo4j`

也就是说，**Neo4j 不是当前项目默认必须使用的主数据库**，而是 Graph RAG 的可选图数据库后端。

## 一句话总结

如果你问“这个项目现在使用的项目数据库是什么”，答案是：

**主数据库是 SQLite，文件是 `Financial-MCP-Agent/data/financial_sessions.db`。**

如果把 RAG 一起算上：

- 业务主库：SQLite
- 向量检索：FAISS/JSON 体系
- 图检索：JSON 回退或 Neo4j
