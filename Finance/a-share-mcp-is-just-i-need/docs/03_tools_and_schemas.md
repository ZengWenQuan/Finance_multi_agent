# 工具与 Schema

工具就是 MCP 的对外能力边界。每个工具都应当：
- 具有稳定的名称（供 LLM 调用）
- 明确入参
- 返回结构化输出

位置说明：
- 工具函数在 `src/tools/`
- 工具注册在 `mcp_server.py`

我们遵循的规则：
1. 工具参数尽量小且明确。
2. 返回值用 Markdown 表格或 JSON 风格结构。
3. 空结果要抛 `NoDataFoundError`（与真实错误区分）。
4. 工具名保持稳定，避免 Prompt 失效。

新增工具步骤：
1. 在 `BaostockDataSource` 中实现方法（或复用已有方法）。
2. 在 `src/tools/` 写一个薄封装调用数据源方法。
3. 在 `mcp_server.py` 注册工具。
4. 在本文件补充说明和示例。
