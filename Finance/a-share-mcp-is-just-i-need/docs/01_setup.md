# 本地运行

前置条件：
- Python 环境已装好项目依赖
- Baostock 依赖可用（用于数据访问）

安装依赖：
```bash
pip install -r /home/irving/workspace/agent_demo/Finance/requirements.txt
pip install baostock
```

本地启动（stdio 模式）：
```bash
cd /home/irving/workspace/agent_demo/Finance/a-share-mcp-is-just-i-need
python mcp_server.py
```

客户端侧配置位置：
- `Financial-MCP-Agent/src/tools/mcp_config.py`
- MCP 客户端通过 `uv run --directory ... python mcp_server.py` 启动此服务。
