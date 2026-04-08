# 测试与排错

本地冒烟测试：
```bash
cd /home/irving/workspace/agent_demo/Finance/a-share-mcp-is-just-i-need
python test_baostock.py
```

常见问题：
- Baostock 登录失败：检查网络和账号状态。
- 没有数据：确认股票代码格式（如 `sh.600000`）和日期范围。
- MCP 工具找不到：检查 `mcp_server.py` 是否注册了该工具。

建议的检查顺序：
1. 在 Python 里直接调用 Baostock API 看是否有数据。
2. 确认 `Financial-MCP-Agent/src/tools/mcp_config.py` 指向正确的服务路径。
3. 查看日志定位工具执行顺序和异常堆栈。
