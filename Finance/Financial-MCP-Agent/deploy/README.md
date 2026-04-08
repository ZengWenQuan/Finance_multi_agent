# 分布式 Docker 部署方案

## 架构概览

```
┌─────────────┐      ┌──────────────────────────────────────────┐
│   浏览器     │      │         Docker 内部网络 fmcp_net           │
│             │      │                                          │
│             │─────▶│  nginx:1.27-alpine :8890                 │
│             │      │    /api/* ──────────────────────────┐    │
│             │      │    /      → 静态前端 HTML/CSS/JS    │    │
└─────────────┘      │                                     ▼    │
                     │  python:3.11-slim :8000 (backend)        │
                     │    FastAPI + LangChain + LangGraph   │    │
                     │    ├── MCP stdio 子进程 ◀──────────┘    │
                     │    │   (a-share-mcp-server)              │
                     │    └── SQLite /app/data/                  │
                     └──────────────────────────────────────────┘
```

关键设计决策：MCP Server 使用 stdio（进程间管道）与 Backend 通信，
不是独立网络服务，因此两者合并在同一容器内。

## 生成的文件

```
deploy/
├── docker-compose.yml      # 编排文件
├── Dockerfile.backend      # 后端镜像
├── nginx/
│   └── nginx.conf          # 反向代理配置
└── start.sh                # 一键启动脚本
```

## 为什么选 python:3.11-slim 而不是其他镜像

| 选项 | 大小 | 备注 |
|------|------|------|
| python:3.11-slim | ~124MB | 推荐，已在本地，glibc 兼容 |
| python:3.11-alpine | ~50MB | baostock/numpy C 扩展在 musl 上编译困难 |
| 自定义 langchain 镜像 | — | 官方没有标准镜像，版本难锁定，不推荐 |

结论：直接在 python:3.11-slim 上 pip install 是最稳定的方案。

## 使用方法

首次启动（构建镜像）：
```bash
bash deploy/start.sh --build
```

日常启动：
```bash
bash deploy/start.sh
```

停止服务：
```bash
bash deploy/start.sh --down
```

查看日志：
```bash
docker compose -f deploy/docker-compose.yml logs -f backend
```

## 数据持久化

| 容器路径 | 宿主机路径 | 说明 |
|---------|-----------|------|
| /app/data | Financial-MCP-Agent/data/ | SQLite 数据库 |
| /app/reports | Financial-MCP-Agent/reports/ | Markdown 报告 |
| /app/logs | Financial-MCP-Agent/logs/ | 运行日志 |
| /app/mcp_server | Finance/a-share-mcp-is-just-i-need/ | MCP stdio 服务器源码 |

## 环境变量说明

.env 文件（Financial-MCP-Agent/.env）：

```env
OPENAI_COMPATIBLE_API_KEY=sk-...
OPENAI_COMPATIBLE_BASE_URL=http://your-vllm:8000/v1
OPENAI_COMPATIBLE_MODEL=Qwen/Qwen2.5-7B-Instruct
```

如果 vLLM 运行在宿主机，BASE_URL 改为：
http://host.docker.internal:8000/v1
