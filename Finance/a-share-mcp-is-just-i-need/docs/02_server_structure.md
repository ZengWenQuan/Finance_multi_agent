# 服务端结构

核心文件：
- `mcp_server.py`：启动 MCP 并注册工具
- `src/baostock_data_source.py`：具体数据源实现
- `src/data_source_interface.py`：数据源抽象接口
- `src/tools/`：工具函数定义
- `src/utils.py`：Baostock 登录、拉取、格式化等公共逻辑

依赖流向：
1. `mcp_server.py` 导入工具函数。
2. 工具函数调用 `BaostockDataSource`。
3. `BaostockDataSource` 调用 Baostock API，并使用 `utils.py` 的辅助方法。

这样的拆分带来：
- 可替换数据源而不改工具签名
- 新增工具只需写一个薄封装并注册
