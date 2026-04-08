"""
MCP服务器配置模块 - 包含连接A股MCP服务器的配置信息
"""
import os

# 支持环境变量覆盖，方便 Docker 容器内使用挂载路径
_DEFAULT_MCP_DIR = r"/home/irving/workspace/agent_demo/Finance/a-share-mcp-is-just-i-need"
MCP_SERVER_DIR = os.getenv("MCP_SERVER_DIR", _DEFAULT_MCP_DIR)

SERVER_CONFIGS = {
    "a_share_mcp_v2": {  
        "command": "uv", 
        "args": [
            "run",  
            "--directory",
            MCP_SERVER_DIR,
            "python",  #
            "mcp_server.py"  # MCP服务器脚本
        ],
        "transport": "stdio",
    }
}
