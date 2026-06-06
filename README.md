# Agent Platform

文件配置 Agent + 单页 Chat 前端。Agent 定义在 `backend/agents/<slug>/`。

## 环境准备

```bash
# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # 填写 DATABASE_URL、模型密钥、ODI_KNOWLEDGE_POSTGRES_URL 等

# 前端
cd frontend
npm install
```

## 启动方式

### 方式一：一键后台启动（无终端日志）

进程在后台运行，日志写入文件（见下文「查看后台日志」）。

```bash
# 项目根目录
./scripts/start.sh

# 停止
./scripts/stop.sh
```

启动后：

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8000 |
| Swagger | http://127.0.0.1:8000/docs |

### 方式二：前后端分开前台启动（推荐调试）

先停掉后台进程，避免端口占用：

```bash
./scripts/stop.sh
```

开 **两个终端**，日志直接打在各自窗口：

**终端 A — 后端**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**终端 B — 前端**

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

调试聊天、MCP、工具调用时，优先看 **终端 A** 的后端输出。

### 查看后台日志

使用 `./scripts/start.sh` 时，日志不在当前终端，需 `tail -f`：

```bash
# 后端
tail -f backend/.run/uvicorn.log

# 前端（另开终端）
tail -f frontend/.run/vite.log
```

### 健康检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/agents
```

## 冒烟测试

```bash
cd backend
source .venv/bin/activate

# 验证 odi-analysis agent 的 postgres MCP 工具已挂载
python scripts/smoke_mcp_agent.py

# 单元测试
pytest tests/ -q
```

## 常见日志说明

| 日志 | 是否阻塞聊天 | 处理 |
|------|-------------|------|
| `Redis connection failed — session cache will use DB only` | 否 | 本地可改 `REDIS_URL=redis://127.0.0.1:6379` 或忽略 |
| `Connected to database: ... odi_knowledge_ai` | — | MCP postgres 正常 |
| `anthropic.AuthenticationError: 401 Unauthorized` | **是** | 修正 `CLAUDE_AZURE_API_KEY` / `CLAUDE_AZURE_FOUNDRY_ENDPOINT` |

`odi-analysis` 使用 `azure_anthropic`，必须在 `backend/.env` 配置：

```bash
CLAUDE_AZURE_API_KEY=<Azure AI Foundry 资源的 API Key>
CLAUDE_AZURE_FOUNDRY_ENDPOINT=https://<resource>.services.ai.azure.com/anthropic
CLAUDE_AZURE_FOUNDRY_MODEL=claude-sonnet-4-6
```

Key 与 Endpoint 必须来自**同一 Azure 资源、同一区域**（例如都是 China East / Southeast Asia 等）。

## 相关文档

- Agent 配置：`backend/agents/README.md`
- 环境变量模板：`backend/.env.example`
