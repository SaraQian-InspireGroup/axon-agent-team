# Agent Platform 架构方案

> 基于 Microsoft Agent Framework (MAF) 的多 Agent 平台，Python 后端 + React 前端。
>
> 版本：v0.6 · 更新日期：2026-06-06

---

## 目录

1. [项目目标](#1-项目目标)
2. [技术选型](#2-技术选型)
3. [目录结构](#3-目录结构)
4. [整体架构](#4-整体架构)
5. [Microsoft Agent Framework 能力映射](#5-microsoft-agent-framework-能力映射)
6. [模型层（GPT / Claude / DeepSeek）](#6-模型层gpt--claude--deepseek)
7. [Tool 与 MCP](#7-tool-与-mcp)
8. [Skill（原生渐进式加载）](#8-skill原生渐进式加载)
9. [ReAct Agent 与流式对话](#9-react-agent-与流式对话)
10. [多 Agent 配置与复用](#10-多-agent-配置与复用)
11. [记忆方案（短期 & 长期）](#11-记忆方案短期--长期)
12. [数据库设计与 Migration](#12-数据库设计与-migration)
13. [API 设计](#13-api-设计)
14. [前端方案（React + AG-UI）](#14-前端方案react--ag-ui)
15. [可观测性与审计](#15-可观测性与审计)
16. [Phase 2 规划](#16-phase-2-规划)
17. [实施路线图](#17-实施路线图)
18. [安全与运维](#18-安全与运维)
19. [参考链接](#19-参考链接)

> **Phase 1 可执行任务清单**见 [PHASE1_TASKS.md](./PHASE1_TASKS.md)

---

## 1. 项目目标

构建一个可配置的 Agent 平台，满足以下核心需求：

| 需求 | Phase 1 | Phase 2 |
|------|---------|---------|
| 基于 MAF，对接 Azure 多模型（GPT / Claude / DeepSeek） | ✅ | |
| MCP / Tool / Skill 配置，跨 Agent 复用 | ✅ | |
| ReAct Agent + 流式对话 | ✅ | |
| 用户可配置多个 Agent，共用底层 Platform 能力 | ✅ | |
| DB Migration 管理，记录完整对话轨迹 | ✅ | |
| 多轮对话 + 短期/长期记忆 | ✅ | |
| 平台公共 Utility 模型（标题生成、历史压缩） | ✅ | |
| Streaming Cancel / Stop（停止生成、修正输入） | | ✅ |
| A2A 多 Agent 协作 | | ✅ |

---

## 2. 技术选型

| 层级 | 选型 | 说明 |
|------|------|------|
| Agent 运行时 | `agent-framework` ≥ 1.0 | MAF 官方 Python SDK，ReAct / MCP / Skill 原生支持 |
| Web API | FastAPI | 异步友好，与 MAF async API 匹配 |
| 前端协议 | AG-UI + SSE | MAF 官方 `agent-framework-ag-ui` 集成 |
| 前端框架 | React + TypeScript | 可用 CopilotKit 或自研 AG-UI 客户端 |
| 主数据库 | PostgreSQL (Neon) | 用户、Agent 配置、对话、审计 |
| 缓存 | Redis | 活跃 Session 热缓存、限流 |
| Migration | Alembic | 版本化 Schema 管理 |
| 观测 | OpenTelemetry | MAF 内置 hook + 自定义 Middleware 审计 |

---

## 3. 目录结构

```
agent-platform/
├── .env                          # 环境变量（不入 git）
├── .gitignore
├── docs/
│   └── ARCHITECTURE.md           # 本文档
│
├── backend/                      # Python Agent Platform
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/             # Migration scripts
│   └── app/
│       ├── main.py               # FastAPI 入口
│       ├── config.py             # 配置加载（含 load_dotenv）
│       ├── api/
│       │   ├── routes/
│       │   │   ├── chats.py
│       │   │   ├── agents.py
│       │   │   ├── users.py
│       │   │   └── agui.py       # AG-UI SSE 端点
│       │   └── deps.py
│       ├── platform/             # Platform 层（MAF 之上）
│       │   ├── model_registry.py # 多模型 Client 工厂
│       │   ├── utility_models.py # 公共 Utility 模型（标题、压缩）
│       │   ├── tool_registry.py  # Function Tool 注册
│       │   ├── mcp_registry.py   # MCP Server 连接管理
│       │   ├── skill_registry.py # SkillsProvider 组装
│       │   ├── agent_factory.py  # 按 DB 配置构建 MAF Agent
│       │   └── session_store.py  # Session 序列化 / Redis 缓存
│       ├── services/
│       │   ├── chat_title.py     # 异步标题生成
│       │   └── history_compaction.py
│       ├── memory/
│       │   ├── postgres_history.py   # 自定义 History Provider
│       │   └── user_memory.py        # 长期记忆 Context Provider
│       ├── middleware/
│       │   └── audit.py          # Tool/MCP/Skill 调用审计
│       ├── db/
│       │   ├── models.py
│       │   └── session.py
│       └── skills/               # 共享 Skill 库（SKILL.md）
│           └── <skill-name>/
│               ├── SKILL.md
│               ├── references/
│               └── scripts/
│
└── frontend/                     # React 前端
    ├── package.json
    └── src/
        ├── App.tsx
        ├── api/                  # AG-UI / REST 客户端
        └── components/
            ├── Chat.tsx
            ├── AgentConfig.tsx
            └── SkillTimeline.tsx # Skill 渐进式加载时间线
```

---

## 4. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        frontend/ (React)                        │
│              AG-UI Client ← SSE → REST API                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                     backend/ (FastAPI)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ API Routes  │  │ Agent Factory│  │ Audit Middleware       │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         │                │                       │              │
│  ┌──────▼────────────────▼───────────────────────▼────────────┐ │
│  │                    Platform Layer                          │ │
│  │  ModelRegistry │ ToolRegistry │ McpRegistry │ SkillRegistry │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│              Microsoft Agent Framework (MAF)                     │
│  Agent │ AgentSession │ SkillsProvider │ MCP Tools │ Middleware │
└──────┬──────────────────────────────┬───────────────────────────┘
       │                              │
┌──────▼──────┐              ┌────────▼────────┐
│ Azure Models│              │ External MCP     │
│ GPT/Claude  │              │ Postgres/MySQL/  │
│ DeepSeek    │              │ PageIndex/...    │
└─────────────┘              └──────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│ PostgreSQL (持久化)  +  Redis (热缓存)       │
└─────────────────────────────────────────────┘
```

### 分层职责

| 层 | 职责 |
|----|------|
| **Frontend** | 聊天 UI、Agent 配置、Skill 加载时间线、Tool 调用可视化 |
| **API** | REST 资源管理 + AG-UI 流式端点 |
| **Platform** | 将 DB 配置翻译为 MAF 运行时对象；跨 Agent 复用 Registry |
| **MAF** | ReAct 循环、Skill 渐进式加载、MCP 协议、Session 管理 |
| **Storage** | 对话历史、Session 快照、审计事件、用户长期记忆 |

---

## 5. Microsoft Agent Framework 能力映射

MAF 是 Semantic Kernel + AutoGen 的继任者，v1.0 已 GA（2026-06），API 稳定。

| 平台需求 | MAF 原生能力 | 我们的扩展 |
|----------|-------------|-----------|
| ReAct Agent | `Agent` 内置 Sense→Plan→Act→Reflect 循环 | — |
| 流式输出 | `agent.run(..., stream=True)` | SSE via AG-UI |
| Function Tools | `@tool` / 函数注册 | `ToolRegistry` 持久化定义 |
| MCP | `MCPStdioTool` / `MCPStreamableHTTPTool` / `MCPWebsocketTool` | `McpRegistry` 按 Agent 动态挂载 |
| **Skill 渐进式加载** | **`SkillsProvider` 四阶段 Progressive Disclosure** | `SkillRegistry` 多源组合 + 按 Agent 过滤 |
| 多轮对话 | `AgentSession` + History Provider | `PostgresHistoryProvider` + Redis |
| 长期记忆 | `ContextProvider` 自定义 | `UserMemoryProvider` + 可选 Mem0 |
| 标题 / 历史压缩 | 无（平台任务） | `UtilityModelRegistry` + 专用小模型 |
| 调用审计 | `FunctionInvocationContext` Middleware | 写入 `messages` 表 |
| 多 Agent 编排 | Workflow（sequential/handoff/group chat） | Phase 2 |
| 跨框架协作 | A2A 协议 | Phase 2 |

---

## 6. 模型层（GPT / Claude / DeepSeek）

### 6.1 ModelProviderRegistry

Platform 层统一工厂，按 Agent 配置的 `model_provider` + `model_name` 实例化 MAF Client：

```python
# platform/model_registry.py（示意）

from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.anthropic import AnthropicClient
from agent_framework.openai import OpenAIChatClient

PROVIDERS = {
    "azure_openai": lambda cfg: AzureOpenAIChatClient(
        api_key=cfg.azure_api_key,
        base_url=cfg.azure_openai_base_url,
        deployment_name=cfg.azure_openai_deployment,
        api_version=cfg.azure_openai_api_version,
    ),
    "azure_anthropic": lambda cfg: AnthropicClient(
        model=cfg.claude_model,
        api_key=cfg.claude_api_key,
        base_url=cfg.claude_base_url,  # https://<resource>.services.ai.azure.com/anthropic
    ),
    "azure_deepseek": lambda cfg: OpenAIChatClient(
        model=cfg.deepseek_model,
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_base_url,  # Azure Foundry 托管端点优先
    ),
}
```

### 6.2 环境变量映射

| 变量 | 用途 |
|------|------|
| `AZURE_API_KEY` | Azure OpenAI / Cognitive Services |
| `AZURE_OPENAI_BASE_URL` | GPT 端点（需以 `/openai` 结尾） |
| `AZURE_OPENAI_API_VERSION` | API 版本 |
| `AZURE_OPENAI_DEPLOYMENT` | 部署名（如 gpt-5.4） |
| `CLAUDE_AZURE_API_KEY` | Claude on Foundry |
| `CLAUDE_AZURE_FOUNDRY_ENDPOINT` | Anthropic **base URL**（`.../anthropic`，非 `/v1/messages`） |
| `CLAUDE_AZURE_FOUNDRY_MODEL` | Claude 模型名 |
| `UTILITY_MODEL_API_KEY` | Utility 模型 API Key（可与主模型相同） |
| `UTILITY_MODEL_BASE_URL` | Utility 端点（通常同 `AZURE_OPENAI_BASE_URL`） |
| `UTILITY_MODEL_API_VERSION` | Utility API 版本 |
| `UTILITY_MODEL_DEPLOYMENT` | Utility 部署名（如 `gpt-4o-mini`） |
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` | Redis 连接串 |

> **注意**：MAF 不会自动加载 `.env`，需在 `main.py` 入口显式调用 `load_dotenv()`。`.env` 内行尾注释可能导致部分 loader 解析异常，生产配置建议去掉行尾 `#` 注释。

### 6.3 DeepSeek 策略

| 方式 | 推荐度 | 说明 |
|------|--------|------|
| Azure Foundry 托管 DeepSeek | ⭐⭐⭐ | 与 MAF `OpenAIChatClient` 兼容最好 |
| 直连 DeepSeek API | ⭐ | OpenAI 兼容层有差异，多轮对话可能需代理（[Issue #1374](https://github.com/microsoft/agent-framework/issues/1374)） |

### 6.4 平台公共 Utility 模型（System Models）

用户配置的 Agent 各自绑定对话模型（可能很贵、很慢）。平台另提供 **与业务 Agent 解耦的公共 Utility 模型**，承担低成本、高频率的后台 LLM 任务。Phase 1 内置两项：

| 用途 | `utility_purpose` | 触发时机 | 输出 |
|------|-------------------|----------|------|
| **Chat 标题生成** | `chat_title` | 首轮对话完成后（异步） | 更新 `chats.title` |
| **会话历史压缩** | `history_compaction` | Compaction 触发 / 超 token 阈值 | `chats.summary` 或压缩后 history |

**设计原则**

- Utility 调用 **不经过** 用户 Agent 的 `AgentSession`，无 tool/skill/mcp，单次短 prompt
- 默认使用 **便宜、快** 的部署（如 `gpt-4o-mini` / `gpt-5.4-mini`），与用户 Agent 模型无关
- 配置集中在 Platform 层，支持 env 默认值 + 未来 DB 覆盖
- 通过 `UtilityModelRegistry` 与 `ModelProviderRegistry` 共用 Client 工厂，但独立 purpose 路由

**环境变量（当前 workspace 已配置）**

```bash
# 对话主模型
AZURE_API_KEY=...
AZURE_OPENAI_BASE_URL=https://<resource>.cognitiveservices.azure.com/openai
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.4

# Utility 模型（标题、历史压缩）— 独立部署，建议 mini
UTILITY_MODEL_API_KEY=...
UTILITY_MODEL_BASE_URL=https://<resource>.cognitiveservices.azure.com/openai
UTILITY_MODEL_API_VERSION=2024-12-01-preview
UTILITY_MODEL_DEPLOYMENT=gpt-4o-mini

# 未设置 UTILITY_MODEL_* 时，config.py fallback 到 AZURE_OPENAI_*
# 未来可选：UTILITY_MODEL_CHAT_TITLE_DEPLOYMENT / UTILITY_MODEL_HISTORY_COMPACTION_DEPLOYMENT
```

**Registry 与 Service（示意）**

```python
# backend/app/platform/utility_models.py

from enum import Enum

class UtilityPurpose(str, Enum):
    CHAT_TITLE = "chat_title"
    HISTORY_COMPACTION = "history_compaction"


class UtilityModelRegistry:
    """解析 purpose → MAF ChatClient；与用户 Agent 模型隔离。"""

    def get_client(self, purpose: UtilityPurpose) -> ChatClient: ...

    async def complete(self, purpose: UtilityPurpose, *, prompt: str, max_tokens: int = 512) -> str: ...


class ChatTitleService:
    """首轮 run 结束后异步生成标题，失败则保留 'New Chat'。"""

    PROMPT = "Generate a concise chat title (max 8 words, same language as user). Reply title only.\n\n{snippet}"

    async def generate_after_first_turn(self, chat_id: str, messages: list[dict]) -> None: ...


class HistoryCompactionService:
    """供 CompactionProvider / 平台阈值调用；使用 utility 模型做摘要。"""

    async def summarize(self, chat_id: str, rows: list[dict], *, target_tokens: int) -> str: ...
```

**与 MAF Compaction 的关系**

- Phase 1e 启用 `SummarizationStrategy` 时，`summarizer_client` **必须**来自 `UtilityModelRegistry.get_client(HISTORY_COMPACTION)`，而非用户 Agent 的 client
- `ChatTitleService` 在 Phase 1d 接入；压缩在 Phase 1e 接入

**未来扩展**（接口预留 `UtilityPurpose` 枚举即可）

- `tool_result_slim`：大 tool 结果自动摘要（与 `ToolResultSlimmer` 可组合）
- `memory_extraction`：从对话抽取长期记忆（对接 `UserMemoryProvider`）

---

## 7. Tool 与 MCP

### 7.1 Function Tools

MAF 原生支持类型安全的 Python 函数作为 Tool：

```python
from agent_framework import tool

@tool
async def search_docs(query: str) -> str:
    """Search internal documentation."""
    ...
```

Platform 将 Tool 定义存 DB（`tools` 表），运行时通过 `ToolRegistry` 解析并注册到 Agent。

### 7.2 MCP 集成

MAF 支持三种传输方式：

| 传输 | MAF 类 | 适用场景 |
|------|--------|----------|
| stdio | `MCPStdioTool` | 本地子进程（如 `npx @modelcontextprotocol/server-postgres`） |
| HTTP SSE | `MCPStreamableHTTPTool` | 远端托管 MCP（PageIndex、自建服务） |
| WebSocket | `MCPWebsocketTool` | 长连接远端 MCP |

```python
from agent_framework import MCPStdioTool, MCPStreamableHTTPTool

postgres_mcp = MCPStdioTool(
    name="postgres",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-postgres", connection_string],
)

pageindex_mcp = MCPStreamableHTTPTool(
    name="pageindex",
    url="https://mcp.pageindex.io/sse",
)
```

### 7.3 跨 Agent 复用

MCP Server 和 Function Tool 在 DB 中独立存储，通过 `agent_tools` / `agent_mcp_servers` 关联表挂载到不同 Agent：

```
tools (共享)  ──┬── agent_tools ── agents
mcp_servers (共享) ──┬── agent_mcp_servers ── agents
```

---

## 8. Skill（原生渐进式加载）

> **重要更正**：MAF 原生支持 Agent Skills，遵循 [agentskills.io](https://agentskills.io/) 开放规范，与 Cursor Skill 的 `SKILL.md` 格式一致。无需 Platform 层重新实现渐进式加载。

### 8.1 四阶段 Progressive Disclosure

```
┌──────────────────────────────────────────────────────────────┐
│ Stage 1: Advertise  (~100 tokens/skill)                      │
│   → skill name + description 注入 system prompt              │
├──────────────────────────────────────────────────────────────┤
│ Stage 2: Load  (< 5000 tokens 推荐)                          │
│   → Agent 调用 load_skill(name) 获取 SKILL.md 完整指令       │
├──────────────────────────────────────────────────────────────┤
│ Stage 3: Read resources  (按需)                              │
│   → Agent 调用 read_skill_resource(skill, path)            │
├──────────────────────────────────────────────────────────────┤
│ Stage 4: Run scripts  (按需)                               │
│   → Agent 调用 run_skill_script(skill, script, args)       │
└──────────────────────────────────────────────────────────────┘
```

10 个 Skill 的固定上下文开销约 **~1000 tokens**，而非全量灌入。

### 8.2 SKILL.md 标准结构

```
expense-report/
├── SKILL.md              # 必需：YAML frontmatter + Markdown 指令
├── scripts/              # 可选：.py 等可执行脚本
│   └── validate.py
├── references/           # 可选：按需加载的参考文档
│   └── POLICY_FAQ.md
└── assets/               # 可选：模板等静态资源
    └── report-template.md
```

`SKILL.md` frontmatter 示例：

```yaml
---
name: expense-report
description: File and validate employee expense reports. Use when asked about expense submissions or reimbursement rules.
metadata:
  author: finance-team
  version: "1.0"
---
```

### 8.3 Skill 来源（MAF 原生支持）

| 来源 | MAF API | 适用场景 |
|------|---------|----------|
| 文件系统 | `SkillsProvider.from_paths(paths)` | 共享 Skill 库，版本化管理 |
| 代码内联 | `InlineSkill(...)` | DB 动态生成、用户自定义 |
| 类定义 | `ClassSkill` 子类 | 复杂逻辑、DI 注入 |
| MCP 远端 | `MCPSkillsSource` (SEP-2640) | 远端 Skill 目录 |

### 8.4 Platform SkillRegistry 设计

```python
from pathlib import Path
from agent_framework import (
    SkillsProvider,
    AggregatingSkillsSource,
    FilteringSkillsSource,
    FileSkillsSource,
    InMemorySkillsSource,
)

def build_skills_provider(agent_config) -> SkillsProvider:
    sources = []

    # 共享文件 Skill
    sources.append(FileSkillsSource(
        paths=[Path("app/skills")],
        script_runner=platform_script_runner,  # 带沙箱的执行器
    ))

    # DB 动态 InlineSkill
    if agent_config.inline_skills:
        sources.append(InMemorySkillsSource(agent_config.inline_skills))

    # MCP 远端 Skill（可选）
    if agent_config.mcp_skill_client:
        sources.append(MCPSkillsSource(agent_config.mcp_skill_client))

    # 按 Agent 配置过滤
    filtered = FilteringSkillsSource(
        AggregatingSkillsSource(sources),
        predicate=lambda s: s.name in agent_config.skill_ids,
    )

    return SkillsProvider(filtered)
```

### 8.5 跨 Agent 复用

- 共享 Skill 目录 `backend/app/skills/` 存放平台级 Skill
- `skills` DB 表记录元数据（name、description、source_type、path）
- `agent_skills` 关联表控制每个 Agent 可见的 Skill 子集
- `FilteringSkillsSource` 在运行时按 Agent 配置过滤

### 8.6 脚本执行安全

MAF 提供的 `SubprocessScriptRunner` 仅适合开发。生产环境 Platform 层需实现：

- 容器 / seccomp 沙箱
- CPU / 内存 / 超时限制
- 脚本白名单
- 结构化审计日志

---

## 9. ReAct Agent 与流式对话

### 9.1 Agent 构建

```python
from agent_framework import Agent

agent = Agent(
    client=model_client,
    name=agent_config.name,
    instructions=agent_config.instructions,
    tools=[*function_tools, *mcp_tools],
    context_providers=[
        skills_provider,
        history_provider,
        user_memory_provider,
    ],
    require_per_service_call_history_persistence=True,  # ReAct 多轮 tool call 时建议开启
)
```

### 9.2 流式 API

```python
async for update in agent.run(user_message, session=session, stream=True):
    if update.text:
        yield {"type": "text", "content": update.text}
    # tool call / skill load 等事件通过 Middleware 审计写入 DB
```

### 9.3 AG-UI 集成

```python
from fastapi import FastAPI
from agent_framework.ag_ui import add_agent_framework_fastapi_endpoint

app = FastAPI()
add_agent_framework_fastapi_endpoint(app, agent, "/agui/{agent_id}")
```

AG-UI 自动处理：SSE 流式、Tool 事件、Human-in-the-loop 审批、State 同步。

---

## 10. 多 Agent 配置与复用

### 10.1 概念模型

```
Platform（共享能力）
├── ModelRegistry      → GPT / Claude / DeepSeek Clients
├── ToolRegistry       → Function Tools
├── McpRegistry        → MCP Server 连接
├── SkillRegistry      → SkillsProvider 多源组合
└── AgentFactory       → 按 DB 配置实例化 MAF Agent

Agent 实例（用户配置）
├── instructions, model_provider, model_name
├── tool_ids[]         → 引用 ToolRegistry
├── mcp_server_ids[]   → 引用 McpRegistry
└── skill_ids[]        → 引用 SkillRegistry（FilteringSkillsSource 过滤）
```

### 10.2 Agent 生命周期

```
用户创建 Agent 配置 (DB)
    → AgentFactory.build(agent_id)
        → 加载 model_client
        → 组装 tools + mcp_tools
        → 构建 SkillsProvider（过滤后）
        → 挂载 HistoryProvider + UserMemoryProvider
        → 返回 MAF Agent 实例（可缓存）
    → 用户发起对话
        → 获取/恢复 AgentSession
        → agent.run(message, session=session, stream=True)
        → Middleware 审计 → 写入 messages 表
```

---

## 11. 记忆方案（短期 & 长期）

### 11.1 MAF 记忆机制概览

| 机制 | MAF 组件 | 存储 | 范围 |
|------|----------|------|------|
| 会话状态 | `AgentSession` | Redis + DB 快照 | 单次 Chat |
| 对话历史 | History Provider | PostgreSQL | 同 Chat 多轮 |
| 注入上下文 | `ContextProvider` | DB / 向量库 | 跨 Chat |
| 摘要压缩 | History Reducer | PostgreSQL | 超长对话 |

### 11.2 Phase 1：多轮对话与短期记忆（详细）

Phase 1 的短期记忆目标：**同一 `chat` 内多轮对话，Agent 能记住前文**。不依赖 Mem0 / RAG / 跨 Chat 记忆（属 Phase 1e 或 Phase 2）。

#### 11.2.1 概念映射

| 平台概念 | MAF 概念 | 说明 |
|----------|----------|------|
| `chats` 表一行 | 一次对话线程 | 用户与某 Agent 的连续会话 |
| `chats.id` | `AgentSession.session_id` | 1:1 绑定，创建 chat 时 `create_session(session_id=chat_id)` |
| `chats.session_state` | `AgentSession.to_dict()` | Provider 在 `session.state` 中的私有数据快照 |
| `messages` 表 | 对话历史源库（全量保真） | 所有类型写入 DB；Provider 投影为 MAF `Message` 注入模型 |
| 单次用户发消息 | 一次 `agent.run()` | 每次 run 传入同一 `session` |

#### 11.2.2 MAF 提供的原生支持

**① AgentSession — 多轮对话的核心**

```python
session = agent.create_session(session_id=str(chat_id))

# 每一轮都传入同一 session
result1 = await agent.run("我叫 Alice，喜欢徒步。", session=session)
result2 = await agent.run("你还记得我吗？", session=session)  # 能记住 Alice

# 跨请求恢复
serialized = session.to_dict()
# → {"type": "session", "session_id": "...", "service_session_id": null, "state": {...}}
resumed = AgentSession.from_dict(serialized)
```

`AgentSession` 是轻量状态容器（[Session 设计文档 0016](https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0016-python-context-middleware.md)）：

- `session_id`：本地会话 ID（我们用 `chat_id`）
- `service_session_id`：远端服务托管会话 ID（Responses API 等；Phase 1 GPT Chat Completions 通常为空）
- `state: dict`：各 Provider 的命名空间数据（History Provider 的 `history_key`、元数据等）

Provider 实例挂在 Agent 上、**无 session 级字段**；session 特有数据只存 `session.state[provider.source_id]`。

**② History Provider — 短期记忆的官方扩展点**

| 内置能力 | 类 | Phase 1 用法 |
|----------|-----|-------------|
| 内存历史 | `InMemoryHistoryProvider(load_messages=True)` | 开发/单测；生产替换为 Postgres 实现 |
| 自定义 DB | `HistoryProvider` 子类 | **Phase 1b 核心工作** |
| 审计副本 | 第二个 Provider：`load_messages=False, store_context_messages=True` | 可选；我们已有 Audit Middleware + messages 表 |
| 历史压缩 | `CompactionProvider` + `SlidingWindowStrategy` 等 | Phase 1e 简单窗口；完整压缩可后置 |
| 计数裁剪 | `MessageCountingChatReducer(N)` | Phase 1e 可选 |

官方自定义 Provider 模式（[Storage 文档](https://learn.microsoft.com/en-us/agent-framework/agents/conversations/storage)）：

```python
from agent_framework import HistoryProvider, Message

class PostgresHistoryProvider(HistoryProvider):
    def __init__(self, db):
        super().__init__("postgres-history", load_messages=True)
        self._db = db

    async def get_messages(self, session_id, *, state=None, **kwargs) -> list[Message]:
        key = (state or {}).get(self.source_id, {}).get("history_key", session_id)
        rows = await self._db.load_history_rows(key)  # 全类型保真；见 11.2.4
        return [Message.from_dict(row) for row in rows]

    async def save_messages(self, session_id, messages, *, state=None, **kwargs) -> None:
        if state is not None:
            state.setdefault(self.source_id, {})["history_key"] = session_id
        await self._db.append_messages(session_id, [m.to_dict() for m in messages])
```

**③ 两种存储模式（Phase 1 选手动本地模式）**

| 模式 | 行为 | Phase 1 |
|------|------|---------|
| **本地 Session 状态** | History Provider 在 `session.state` / DB 存消息，每次 run 注入模型 | ✅ 采用 |
| **Service-managed** | 服务端存历史，`service_session_id` 指向远端 conversation | ❌ 不采用（GPT Chat API 无原生会话；Claude 视端点而定） |

注意：若已绑定 `service_session_id`，不可与本地 History Provider 混用（框架会报错）。

**④ ReAct Tool Loop 的历史持久化时机**

默认：`agent.run()` 整个 ReAct 循环结束后，History Provider **一次性**写入。

开启 `require_per_service_call_history_persistence=True` 后：每次 model call（含 tool 循环内）后都持久化，更接近 service-managed 行为。

Phase 1 **建议开启**，原因：
- Tool/MCP/Skill 多轮调用时，中途失败不丢已完成的 tool 轮次
- 为 Phase 2 Cancel/Stop 的历史一致性打基础

**⑤ 流式场景的最终化**

```python
stream = agent.run(message, session=session, stream=True)
async for update in stream:
    yield update
final = await stream.get_final_response()  # 触发 History Provider 的 save 钩子
```

`get_final_response()` 会执行 stream result hooks（持久化 thread/conversation 状态）。Phase 1 流式端点**必须**在消费结束后调用（正常完成路径），否则 history 可能不落库。

参考：[PR #3882 流式 finalize 修复](https://github.com/microsoft/agent-framework/pull/3882)

**⑥ 多 Provider 规则**

- 仅 **一个** History Provider 设 `load_messages=True`（主历史）
- 可叠加 `CompactionProvider`，通过 `history_source_id` 指向主 Provider
- SkillsProvider / UserMemoryProvider 等同属 `context_providers`，与 History 并行

#### 11.2.3 Phase 1 端到端流程

```
┌─────────┐     POST /chats/{id}/messages      ┌──────────────┐
│ React   │ ─────────────────────────────────▶ │ FastAPI      │
└─────────┘                                    └──────┬───────┘
                                                      │
                    ┌─────────────────────────────────▼────────────────────────┐
                    │ 1. Redis GET session:{chat_id}                           │
                    │    命中 → AgentSession.from_dict()                       │
                    │    未命中 → DB chats.session_state → from_dict()         │
                    │           或 agent.create_session(session_id=chat_id)    │
                    ├──────────────────────────────────────────────────────────┤
                    │ 2. AgentFactory.build(agent_id)  # Provider 配置须一致   │
                    ├──────────────────────────────────────────────────────────┤
                    │ 3. PostgresHistoryProvider.get_messages()                │
                    │    → 从 messages 表组装 MAF Message 列表                 │
                    ├──────────────────────────────────────────────────────────┤
                    │ 4. agent.run(user_msg, session=session, stream=True)     │
                    │    → MAF 注入历史 + 本轮输入 → 模型 → Tools/Skills...    │
                    ├──────────────────────────────────────────────────────────┤
                    │ 5. Audit Middleware → messages 表（全事件轨）              │
                    ├──────────────────────────────────────────────────────────┤
                    │ 6. stream 结束 → get_final_response()                    │
                    │    → History Provider save_messages()                    │
                    ├──────────────────────────────────────────────────────────┤
                    │ 7. session.to_dict() → Redis SET + DB chats 更新         │
                    └──────────────────────────────────────────────────────────┘
```

#### 11.2.4 三层存储与历史纳入范围

对话相关数据分三层，职责不同：

```
PostgreSQL (messages)     源库，全量保真，不可丢类型
        │
        ├─▶ History Provider get_messages()  → 组装 MAF Message → 注入模型（Phase 1 全量）
        │
        └─▶ HistoryProjection.project_for_cache()  → Redis 热缓存（Phase 1 全量；未来 Tool Slim）
```

**PostgreSQL + 模型历史：全类型纳入**

用户要求 mcp / skill / reasoning 均 **存 DB 且进入多轮历史**（供后续轮次模型可见）。Phase 1 不做类型排除。

| message_type | 写入 DB | 进入模型历史 | MAF 映射 |
|--------------|---------|-------------|----------|
| `text` (user/assistant) | ✅ | ✅ | `user` / `assistant` |
| `tool_call` / `tool_result` | ✅ | ✅ 原子成对 | `assistant`(function_call) + `tool` |
| `mcp_call` / `mcp_result` | ✅ | ✅ 原子成对 | 同 function 消息 |
| `skill_load` | ✅ | ✅ | `tool` 结果（`load_skill` 返回的 SKILL.md 正文） |
| `skill_resource` | ✅ | ✅ | `tool` 结果（`read_skill_resource` 内容） |
| `skill_script` | ✅ | ✅ | `tool` 结果（脚本 stdout/摘要） |
| `reasoning` | ✅ | ✅ | **独立** `assistant` message，内容类型为 `TextReasoningContent`（非 `text`） |

`PostgresHistoryProvider.load_history_rows()` 按 `sequence` 读取全表相关行，`to_maf_messages()` 保证 **MessageGroup 原子性**（tool call 与 result 不拆散），与 MAF Compaction 的 `ToolCall` group 语义一致。

#### 11.2.4b Reasoning 与 Text 的显式区分

`reasoning` 与 `text`（assistant 最终回复）**必须分轨存储、分轨展示、分轨回放**，不可混为一条普通 assistant 文本。

**三层标识**

| 层 | 字段 / 类型 | 作用 |
|----|-------------|------|
| DB | `messages.message_type = 'reasoning'` | 持久化、查询、UI 渲染（折叠/思考过程样式） |
| DB | `messages.role = 'assistant'` | 与最终回复同属 assistant 侧，但 type 不同 |
| MAF 回放 | `TextReasoningContent` | 注入模型历史时用 MAF 原生推理内容类型，非 `Content.from_text()` |
| MAF 内部 | `Message.additional_properties.platform_message_type` | 平台标记，`'reasoning'`（不发给外部 API） |

**写入（流式解析 `AgentResponseUpdate`）**

```python
from agent_framework import TextReasoningContent, TextContent

for content in update.contents or []:
    if isinstance(content, TextReasoningContent):
        await db.insert_message(
            chat_id=chat_id,
            role="assistant",
            message_type="reasoning",  # 明确不是 text
            content=content.text,
            metadata={
                "model": update.model_id,
                "reasoning_id": (content.additional_properties or {}).get("reasoning_id"),
                "protected_data": getattr(content, "protected_data", None),
            },
        )
    elif isinstance(content, TextContent) or isinstance(content, str):
        await db.insert_message(..., message_type="text", ...)
```

**读回 MAF 历史（`to_maf_messages`）**

```python
from agent_framework import Message, TextReasoningContent, Content

def row_to_maf_message(row: dict) -> Message:
    if row["message_type"] == "reasoning":
        return Message(
            role="assistant",
            contents=[
                TextReasoningContent(
                    text=row["content"],
                    additional_properties=row.get("metadata") or {},
                )
            ],
            additional_properties={"platform_message_type": "reasoning"},
        )
    if row["message_type"] == "text" and row["role"] == "assistant":
        return Message(role="assistant", contents=[Content.from_text(row["content"])])
    # ... user / tool / function 等
```

**同一轮内的顺序**

一次 `agent.run()` 可能先流式输出 `reasoning`，再输出 `text`。按 `sequence` 严格排序，例如：

```
sequence 10: reasoning  "需要先查订单状态..."
sequence 11: tool_call   get_order
sequence 12: tool_result {...}
sequence 13: reasoning  "根据结果组织答复..."
sequence 14: text       "您的订单已发货..."
```

**前端**：SSE / AG-UI 事件携带 `message_type`；`reasoning` 用可折叠「思考过程」组件，**不**与最终气泡混排。

**Compaction 注意**：`SummarizationStrategy` 可配置是否纳入 reasoning；Phase 1e 建议 **摘要时剥离 reasoning 正文**，只保留 text + tool Outcome，避免推理噪声进入摘要（`metadata` 可记 `reasoning_turns_omitted: true`）。

**Redis：Session 快照 + 可投影历史（未来 Slim 仅作用于此层）**

- Phase 1：`session.to_dict()` + 可选缓存最近 N 条 history 的**完整副本**
- 未来：写入 Redis 前经 `HistoryProjection` + `ToolResultSlimmer`，**只瘦身 tool/mcp 的 result 体**；DB 仍保真
- Slim **不**应用于 skill/reasoning/text（除非未来单独策略）

#### 11.2.4a ToolResultSlimmer 扩展接口（Phase 1 空实现，未来按 Tool 定制）

未来 tool 结果可能很大（检索、SQL、MCP 全量 JSON），进入 Redis 前需按 tool 定制瘦身；**Phase 1 使用 `PassthroughToolSlimmer`（原样透传）**，但接口先行定义便于重载。

```python
# backend/app/memory/slimmer.py

from typing import Protocol, runtime_checkable

@runtime_checkable
class ToolResultSlimmer(Protocol):
    """按 tool/mcp 定制 result 瘦身，仅用于 Redis 历史投影，不改 DB。"""

    def supports(self, *, message_type: str, tool_name: str | None) -> bool: ...

    async def slim(
        self,
        *,
        message_type: str,       # tool_result | mcp_result | skill_script
        tool_name: str | None,
        content: str,
        metadata: dict,
    ) -> str: ...


class PassthroughToolSlimmer:
    """Phase 1 默认：不瘦身。"""

    def supports(self, *, message_type: str, tool_name: str | None) -> bool:
        return message_type in ("tool_result", "mcp_result", "skill_script")

    async def slim(self, *, message_type: str, tool_name: str | None, content: str, metadata: dict) -> str:
        return content


class ToolSlimmerRegistry:
    """按 tool_name 注册定制 Slimmer；未命中则 fallback。"""

    def __init__(self, fallback: ToolResultSlimmer | None = None):
        self._by_tool: dict[str, ToolResultSlimmer] = {}
        self._fallback = fallback or PassthroughToolSlimmer()

    def register(self, tool_name: str, slimmer: ToolResultSlimmer) -> None:
        self._by_tool[tool_name] = slimmer

    def resolve(self, tool_name: str | None) -> ToolResultSlimmer:
        if tool_name and tool_name in self._by_tool:
            return self._by_tool[tool_name]
        return self._fallback


class HistoryProjection:
    """DB 全量行 → Redis 缓存行；Phase 1 project_for_cache 等同 identity。"""

    def __init__(self, registry: ToolSlimmerRegistry):
        self._registry = registry

    async def project_for_cache(self, rows: list[dict]) -> list[dict]:
        out = []
        for row in rows:
            if row["message_type"] in ("tool_result", "mcp_result", "skill_script"):
                slim = self._registry.resolve(row["metadata"].get("tool_name"))
                if slim.supports(message_type=row["message_type"], tool_name=row["metadata"].get("tool_name")):
                    row = {**row, "content": await slim.slim(
                        message_type=row["message_type"],
                        tool_name=row["metadata"].get("tool_name"),
                        content=row["content"] or "",
                        metadata=row["metadata"],
                    )}
            out.append(row)
        return out
```

未来示例（Phase 2+）：`PostgresSearchSlimmer` 只保留 top-3 片段；`PageIndexSlimmer` 只保留 page_id + 摘要。

`tools` 表可扩展 `slimmer_class` 字段指向注册名，Agent 挂载 tool 时自动 `registry.register(tool.name, slimmer)`。

#### 11.2.5 Agent 构建（Phase 1 推荐配置）

```python
agent = Agent(
    client=model_client,
    name=agent_config.name,
    instructions=agent_config.instructions,
    tools=[*function_tools, *mcp_tools],
    context_providers=[
        PostgresHistoryProvider(db),
        skills_provider,  # 无状态，不替代 History
    ],
    require_per_service_call_history_persistence=True,
    middleware=[audit_middleware],
)
```

#### 11.2.6 MAF 短期记忆：轮次 / Token 上限与压缩（框架能力）

**框架没有固定的「最多 N 轮」**——轮次理论上不受 MAF 限制，实际上限来自 **所用模型的 context window**（如 128K）。历史随每轮 `agent.run()` 累积，全部注入下一次 model call，直到：
- 触发模型/API 的 context length 错误，或
- 平台配置的 **Compaction** 在调用前削减历史。

| 层级 | 谁限制 | 机制 |
|------|--------|------|
| 硬上限 | 模型 context window | Azure/OpenAI/Anthropic 部署规格 |
| 软控制 | MAF `CompactionProvider` | 每次 model call **之前**（含 tool loop 内）压缩 |
| 简单裁剪 | `MessageCountingChatReducer(N)` | 仅 in-memory History Provider |
| 平台策略 | `agents.config` | `token_budget`、`max_turns` 等，驱动 Compaction trigger |

**CompactionProvider（官方推荐的长对话方案，当前 experimental）**

仅在 **本地 History Provider 模式**下生效（我们 Phase 1 采用）；service-managed 会话无效。

核心概念（[Compaction 文档](https://learn.microsoft.com/en-us/agent-framework/agents/conversations/compaction)）：
- 操作单位是 **MessageGroup**（user 一轮、assistant 文本、tool_call+results 原子组）
- **Trigger**：何时开始压（`TokensExceed`、`TurnsExceed`、`MessagesExceed`、`GroupsExceed`…）
- **Target**：压到什么程度停止
- **before_strategy**：注入模型**前**压缩（影响当前轮可见上下文）
- **after_strategy**：写入 History Provider **后**压缩（影响后续轮存储）

内置策略（由温和到激进）：

| 策略 | 作用 |
|------|------|
| `ToolResultCompactionStrategy` | 旧 tool 组折叠为短摘要 `[Tool results: ...]` |
| `SummarizationStrategy` | LLM 摘要旧对话，插入 `Summary` 组 |
| `SlidingWindowStrategy` | 只保留最近 N 个 group / turn |
| `TruncationStrategy` | 按 token 硬截断最旧 group |
| `TokenBudgetComposedStrategy` | 多策略流水线 |

官方示例（token 预算 16K）：

```python
from agent_framework import CompactionProvider, InMemoryHistoryProvider
from agent_framework._compaction import (
    CharacterEstimatorTokenizer,
    SlidingWindowStrategy,
    SummarizationStrategy,
    TokenBudgetComposedStrategy,
    ToolResultCompactionStrategy,
)

tokenizer = CharacterEstimatorTokenizer()  # 启发式 4 字符/token；可换模型专用 tokenizer

pipeline = TokenBudgetComposedStrategy(
    token_budget=16_000,
    tokenizer=tokenizer,
    strategies=[
        ToolResultCompactionStrategy(keep_last_tool_call_groups=1),
        SummarizationStrategy(client=summarizer_client, target_count=4, threshold=2),
        SlidingWindowStrategy(keep_last_groups=20),
    ],
)

history = PostgresHistoryProvider(db)
compaction = CompactionProvider(
    before_strategy=pipeline,
    after_strategy=ToolResultCompactionStrategy(keep_last_tool_call_groups=3),
    history_source_id=history.source_id,
)
```

**平台 Phase 1 / 1e 策略建议**

| 阶段 | 压缩 |
|------|------|
| Phase 1b | 不启用 Compaction；`token_budget` 仅监控/日志 |
| Phase 1e | 启用 `CompactionProvider`；`token_budget` 按模型设（如 128K 模型用 100K 预算留 tool/skills 余量） |
| 备选 | `chats.summary` 平台侧摘要 + Provider 注入，与 MAF Summarization 二选一或叠加 |

**与 Tool Slim 的分工**

| 机制 | 作用对象 | 时机 | 目的 |
|------|----------|------|------|
| `ToolResultSlimmer` | 单条 tool/mcp result | 写 Redis 投影时 | 减缓存体积；**DB 全量** |
| `ToolResultCompactionStrategy` | 历史中的旧 tool 组 | 每轮 model call 前/后 | 减模型 context token |
| `SummarizationStrategy` | 旧 user/assistant 轮次 | 同上 | 语义保留、大幅减 token |

Phase 1：**DB 与模型历史均全量**；Redis 全量透传；Compaction 与 Slim 均后置。

#### 11.2.7 平台必须自研的部分（MAF 不包）

| 模块 | 职责 | 原因 |
|------|------|------|
| `PostgresHistoryProvider` | DB ↔ MAF `Message` 转换 | 官方只给模式，无 PostgreSQL 实现 |
| `SessionStore` | Redis 热缓存 + `chats.session_state` 双写 | 跨 API 实例恢复 session |
| `chat_id ↔ session_id` 绑定 | 创建 chat 时初始化 session | 业务 ID 与 MAF 对齐 |
| `to_maf_messages()` | DB 全类型行 → MAF `Message`（含 mcp/skill/reasoning） | 保证 MessageGroup 原子性 |
| `HistoryProjection` + `ToolSlimmerRegistry` | Redis 投影；Phase 1 透传 | 未来按 tool 定制瘦身 |
| 流式 `get_final_response()` 编排 | SSE 正常结束时 finalize | 否则 history 不落库 |
| Agent 配置版本兼容 | session 反序列化时 Provider 一致 | 官方要求：同配置 restore |
| 新 chat vs 续聊 API 语义 | `POST /chats` vs `POST /chats/{id}/messages` | 平台 API 层 |

**Phase 1 明确不做**：Mem0、跨 Chat 记忆、`CompactionProvider` 完整管线、service-managed session。

#### 11.2.8 最佳实践清单

1. **始终 `agent.create_session(session_id=chat_id)`**，不要每轮新建 session
2. **持久化整个 `AgentSession`**（`to_dict()`），不只存 message 文本
3. **Provider 无 session 状态**；`history_key` 等放 `session.state[source_id]`
4. **主 History Provider 唯一** `load_messages=True`
5. **ReAct Agent 开启** `require_per_service_call_history_persistence=True`
6. **流式必须 finalize**；异常中断的 Cancel 策略留 Phase 2
7. **恢复 session 时 Agent/Provider 配置与创建时一致**（model、tools、skills 变更需迁移策略）
8. **DB 全量保真**：mcp / skill / reasoning 均入库且进入 Provider 历史；Slim 仅作用于 Redis 投影
9. **Compaction 与 Slim 分工**：前者减模型 token，后者减 Redis 体积；均不删 DB 源数据

#### 11.2.9 Redis 热缓存

```
Key:   session:{chat_id}
Value: {
         "session": AgentSession.to_dict(),
         "history": HistoryProjection.project_for_cache(db_rows)  # Phase 1 全量
       }
TTL:   30min（可配置）

失效：chat 删除、显式 session 重置、Agent 配置 breaking change
```

Redis 未命中时从 `chats.session_state` + DB `messages` 重建；均无时创建新 session。

### 11.3 长期记忆（跨 Chat / 跨 Session）

采用 **分层组合**，而非单一方案：

```
Layer 1: 用户偏好/事实（Platform 自建）
    UserMemoryContextProvider
    → 启动时从 user_memories 表加载
    → 注入 system instructions 片段
    例：「用户是素食者」「项目技术栈是 Python + FastAPI」

Layer 2: 对话摘要（Platform 自建）
    → 当 messages 超过 N 条，触发 LLM 摘要
    → 存入 chats.summary
    → History Provider 注入 summary 替代早期历史

Layer 3: Mem0 自动记忆（可选）
    Mem0ContextProvider(api_key, user_id)
    → 自动抽取/召回跨会话记忆
    → 适合开放域个人助手场景

Layer 4: RAG 知识库（Phase 2）
    → ContextProvider + 向量检索
    → 适合企业知识库问答
```

### 11.4 推荐 Phase 1 组合

| 类型 | 方案 |
|------|------|
| 短期 | `PostgresHistoryProvider` + Redis 热缓存 |
| 长期 | `UserMemoryContextProvider`（`user_memories` 表） |
| 标题 | `ChatTitleService` + Utility 模型 `chat_title`（Phase 1d） |
| 压缩 | `HistoryCompactionService` + Utility 模型 `history_compaction` + `CompactionProvider`（Phase 1e） |
| 可选 | Mem0（按需启用） |

### 11.5 Context Provider 实现要点

```python
from agent_framework import ContextProvider, Context

class UserMemoryContextProvider(ContextProvider):
    async def invoking(self, messages, *, session, **kwargs) -> Context:
        memories = await db.get_user_memories(session.user_id)
        instructions = format_memories(memories)
        return Context(instructions=instructions, messages=[], tools=[])

    async def invoked(self, request_messages, response_messages, *, session, **kwargs):
        # 可选：从对话中抽取新记忆写入 user_memories
        ...
```

---

## 12. 数据库设计与 Migration

使用 **Alembic** 进行版本化管理。所有 Migration 文件存放于 `backend/alembic/versions/`。

### 12.1 ER 关系

```
users ──┬── chats ──── messages
        ├── agents ──┬── agent_tools
        │            ├── agent_mcp_servers
        │            └── agent_skills
        └── user_memories

tools (共享)
mcp_servers (共享)
skills (共享)
```

### 12.2 表结构

#### users

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### agents

```sql
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    instructions    TEXT NOT NULL,
    model_provider  VARCHAR(50) NOT NULL,  -- azure_openai | azure_anthropic | azure_deepseek
    model_name      VARCHAR(100) NOT NULL,
    config          JSONB DEFAULT '{}',    -- 扩展配置（temperature 等）
    a2a_endpoint    VARCHAR(500),          -- Phase 2 预留
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### chats

```sql
CREATE TABLE chats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    agent_id        UUID NOT NULL REFERENCES agents(id),
    title           VARCHAR(500),
    session_state   JSONB,                 -- AgentSession.to_dict() 快照
    summary         TEXT,                  -- 长期摘要
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### messages（核心审计表）

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,   -- user | assistant | system | tool
    content         TEXT,                   -- 文本内容（可为空，事件类消息 content 在 metadata）
    message_type    VARCHAR(30) NOT NULL,   -- 见下方枚举
    metadata        JSONB DEFAULT '{}',
    parent_id       UUID REFERENCES messages(id),  -- tool_call → tool_result 关联
    sequence        INTEGER NOT NULL,       -- 对话内顺序
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_chat_id ON messages(chat_id, sequence);
CREATE INDEX idx_messages_type ON messages(message_type);
```

**message_type 枚举**：

| 类型 | 说明 | metadata 示例 |
|------|------|---------------|
| `text` | 用户/助手文本 | `{tokens_in, tokens_out}` |
| `reasoning` | 模型推理过程（**≠ text**） | `{model, reasoning_id?, protected_data?}`；MAF 回放用 `TextReasoningContent` |
| `tool_call` | Function Tool 调用 | `{tool_name, arguments}` |
| `tool_result` | Function Tool 结果 | `{tool_name, result, duration_ms}` |
| `mcp_call` | MCP Tool 调用 | `{mcp_server, tool_name, arguments}` |
| `mcp_result` | MCP Tool 结果 | `{mcp_server, result, duration_ms}` |
| `skill_load` | load_skill 调用 | `{skill_name, content_length}` |
| `skill_resource` | read_skill_resource | `{skill_name, resource_path}` |
| `skill_script` | run_skill_script | `{skill_name, script_name, args, result}` |
| `error` | 运行错误 | `{error_type, message}` |

#### 共享资源表

```sql
CREATE TABLE tools (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    tool_type   VARCHAR(20) NOT NULL,       -- function
    definition  JSONB NOT NULL,             -- 函数 schema / 模块路径
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mcp_servers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    transport   VARCHAR(20) NOT NULL,       -- stdio | http_sse | websocket
    connection  JSONB NOT NULL,             -- {command, args} 或 {url}
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(64) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,       -- file | inline | mcp
    source_path VARCHAR(500),               -- 文件路径或 MCP 引用
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_tools (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tool_id  UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, tool_id)
);

CREATE TABLE agent_mcp_servers (
    agent_id      UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    mcp_server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, mcp_server_id)
);

CREATE TABLE agent_skills (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);
```

#### user_memories（长期记忆）

```sql
CREATE TABLE user_memories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    key         VARCHAR(255) NOT NULL,
    value       TEXT NOT NULL,
    source      VARCHAR(50),               -- explicit | extracted | mem0
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, key)
);
```

### 12.3 Migration 工作流

```bash
# 初始化
cd backend
alembic init alembic  # 首次

# 创建 migration
alembic revision --autogenerate -m "create core tables"

# 执行
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 13. API 设计

### 13.1 REST 端点

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/users` | 创建用户 |
| `GET` | `/api/v1/users/{id}` | 获取用户 |
| `POST` | `/api/v1/agents` | 创建 Agent 配置 |
| `GET` | `/api/v1/agents` | 列出用户的 Agent |
| `GET` | `/api/v1/agents/{id}` | 获取 Agent 详情 |
| `PUT` | `/api/v1/agents/{id}` | 更新 Agent 配置 |
| `DELETE` | `/api/v1/agents/{id}` | 删除 Agent |
| `POST` | `/api/v1/chats` | 创建新对话 |
| `GET` | `/api/v1/chats` | 列出对话 |
| `GET` | `/api/v1/chats/{id}/messages` | 获取对话消息（含事件） |
| `POST` | `/api/v1/chats/{id}/messages` | 发送消息（非流式） |
| `GET` | `/api/v1/tools` | 列出可用 Tools |
| `GET` | `/api/v1/mcp-servers` | 列出 MCP Servers |
| `GET` | `/api/v1/skills` | 列出 Skills |

### 13.2 流式端点

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/agui/{agent_id}` | AG-UI SSE 流式对话（推荐） |
| `POST` | `/api/v1/chats/{id}/stream` | 原生 SSE 流式（备选） |

### 13.3 发送消息流程

```
POST /api/v1/chats/{chat_id}/stream
Body: { "content": "用户消息" }

SSE Events:
  data: {"type": "text", "content": "你好"}
  data: {"type": "skill_load", "skill": "expense-report"}
  data: {"type": "tool_call", "name": "search_docs", "args": {...}}
  data: {"type": "tool_result", "name": "search_docs", "result": "..."}
  data: {"type": "text", "content": "根据政策..."}
  data: {"type": "done", "message_id": "uuid"}
```

---

## 14. 前端方案（React + AG-UI）

### 14.1 技术选型

| 组件 | 选型 |
|------|------|
| 框架 | React 18 + TypeScript + Vite |
| AG-UI 客户端 | CopilotKit（官方示例最多）或 `@ag-ui/client` |
| 状态管理 | Zustand / React Query |
| UI | Tailwind CSS + shadcn/ui |

### 14.2 核心页面

| 页面 | 功能 |
|------|------|
| **Chat** | 流式对话、Tool/Skill 事件时间线 |
| **AgentConfig** | 创建/编辑 Agent（模型、Tools、MCP、Skills） |
| **SkillTimeline** | 展示 Skill 渐进式加载过程（advertise → load → read → script） |
| **ChatHistory** | 历史对话列表 |

### 14.3 Skill 时间线 UI

参考 MAF 社区实践，将 Skill 四阶段可视化为操作时间线：

```
[Advertised] expense-report, code-style, incident-triage
[Loaded]     expense-report (2.1 KB instructions)
[Read]       expense-report/references/POLICY_FAQ.md
[Script]     expense-report/scripts/validate.py → success
[Response]   根据公司政策，您的报销金额为...
```

### 14.3 AG-UI 连接

```typescript
// frontend/src/api/agent.ts
import { HttpAgent } from "@ag-ui/client";

const agent = new HttpAgent({
  url: `${API_BASE}/agui/${agentId}`,
});

// CopilotKit 集成
<CopilotKit runtimeUrl={`${API_BASE}/agui/${agentId}`}>
  <CopilotChat />
</CopilotKit>
```

---

## 15. 可观测性与审计

### 15.1 Audit Middleware

拦截 MAF 所有 Function / MCP / Skill 调用，写入 `messages` 表：

```python
from agent_framework import FunctionInvocationContext

async def audit_middleware(
    context: FunctionInvocationContext,
    call_next,
    *,
    chat_id: str,
    db,
):
    tool_name = context.function.name
    is_skill = tool_name in ("load_skill", "read_skill_resource", "run_skill_script")

    msg_type = "skill_load" if tool_name == "load_skill" else \
               "skill_resource" if tool_name == "read_skill_resource" else \
               "skill_script" if tool_name == "run_skill_script" else \
               "tool_call"

    call_msg = await db.insert_message(
        chat_id=chat_id,
        role="tool",
        message_type=msg_type,
        metadata={"tool_name": tool_name, "arguments": context.arguments},
    )

    start = time.monotonic()
    await call_next(context)
    duration_ms = (time.monotonic() - start) * 1000

    await db.insert_message(
        chat_id=chat_id,
        role="tool",
        message_type=msg_type.replace("_call", "_result"),
        parent_id=call_msg.id,
        metadata={
            "tool_name": tool_name,
            "result": str(context.result)[:2000],
            "duration_ms": duration_ms,
        },
    )
```

### 15.2 OpenTelemetry

MAF 内置 OpenTelemetry 集成，Platform 层追加：

- Span: `agent.run` → `tool.call` → `skill.load`
- Attributes: `agent_id`, `chat_id`, `model`, `tokens`

---

## 16. Phase 2 规划

Phase 2 在 Phase 1 可用对话基础上，补齐 **流式取消/停止** 与 **A2A 多 Agent 协作** 两类能力。

### 16.1 Streaming Cancel / Stop

#### 背景与约束

用户在流式生成过程中可能需要：
- **Stop**：停止当前生成，不再接收后续输出
- **Edit & Resend**：发现输入有误，停止当前生成并发送修正后的消息

MAF 当前状态（截至 2026-06）：
- **尚无**稳定的 `ResponseStream.cancel()` 公开 API（社区讨论：[Discussion #5548](https://github.com/microsoft/agent-framework/discussions/5548)）
- 强行中断 stream 并保存 partial 回复**极易污染 history**（半截 tool call JSON、tool call/result 不配对、reasoning 片段残留）
- 维护者推荐用 **Middleware 终止** 保历史一致性，而非 hack `_consumed` 私有标志

| 场景 | MAF 原生支持 | Phase 2 Platform 策略 |
|------|-------------|----------------------|
| 用户点 Stop，停止展示 | 部分 | 客户端断 SSE + Run 状态机解锁 |
| Stop 后立刻发新消息 | 需自建 | `RunManager` 与 MAF Session 解耦 |
| Stop 后保存 partial 回复 | 无稳定 API | 按取消时机有条件写入 |
| ReAct 阻止下一轮 model call | `MiddlewareTermination` / `context.terminate` | `StopRequestedMiddleware` |
| 长任务服务端取消 | Responses API `DELETE /responses/{id}` | Background run 专用 |

#### MAF 机制分层（供 Platform 选用）

**Layer 1 — Middleware 终止（官方推荐，历史最安全）**

用于 ReAct 多轮 tool loop，阻止进入下一轮 model call：

```python
from agent_framework import AgentMiddleware, AgentContext, MiddlewareTermination

class StopRequestedMiddleware(AgentMiddleware):
    def __init__(self, stop_event: asyncio.Event):
        self._stop = stop_event

    async def process(self, context: AgentContext, call_next):
        if self._stop.is_set():
            raise MiddlewareTermination
        await call_next()
```

Function 层可用 `context.terminate = True` 立即退出 function calling loop（[PR #2868](https://github.com/microsoft/agent-framework/pull/2868)）。

Agent 配置建议：终止可能发生在 tool loop 中时，开启 `require_per_service_call_history_persistence=True`。

参考：[Termination & Guardrails](https://learn.microsoft.com/en-us/agent-framework/agents/middleware/termination)

**Layer 2 — asyncio Task 取消**

将 `agent.run(stream=True)` 包装为 `asyncio.Task`，Stop 时 `task.cancel()`，在 `CancelledError` 中清理 Run 状态。适合尽快释放资源、解锁聊天输入，history 写入仍需 Platform 规则兜底。

**Layer 3 — Background Response 服务端取消**

仅 OpenAI Responses API 系 Agent（`AzureOpenAIResponsesClient`）支持 `options={"background": True}` 及底层 `DELETE /responses/{responseId}`。

注意：`CancellationToken` / `task.cancel()` **只取消客户端**，不保证停止服务端 processing（[设计文档 0009](https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0009-support-long-running-operations.md)）。

流中断后的 `continuation_token` 用于**断线重连**，不是用户主动 Stop。

**不推荐 — `_consumed` hack**

社区 workaround（设 `response._consumed = True` 后 `get_final_response()`）为私有 API，可能跳过 finalizer，**不用于生产**。

#### Platform 设计方案

**Run 状态机（与 MAF AgentSession 解耦）**

```
┌──────────┐  start   ┌─────────┐  cancel  ┌───────────┐
│  idle    │ ───────▶ │ running │ ───────▶ │ cancelled │
└──────────┘          └────┬────┘          └───────────┘
                           │ complete
                           ▼
                      ┌───────────┐
                      │ completed │
                      └───────────┘
```

Redis 注册表：`run:{run_id}` → `{chat_id, status, task_id, response_id?, started_at}`

每个 chat 同时只允许一个 `running` run（发新消息前须 cancel 或等待完成）。

**时序（Stop → 修正输入）**

```
用户发消息 ──▶ 创建 run_id，锁定 chat
              ──▶ agent.run(stream=True) 包装为 Task
              ──▶ SSE 推送 chunks

用户点 Stop ──▶ POST /api/v1/runs/{run_id}/cancel
              ──▶ stop_event.set() + task.cancel()
              ──▶ 前端 AbortController 断开 SSE
              ──▶ chat 解锁，允许新输入

用户修正发消息 ──▶ 可选：标记上条 user message 为 superseded
                ──▶ 创建新 run，同一 AgentSession 继续
```

**SSE 消费循环（示意）**

```python
async def stream_to_client(run_id: str, stream, request: Request):
    collected_text = []
    try:
        async for update in stream:
            if await run_manager.is_cancelled(run_id):
                break
            if await request.is_disconnected():
                await run_manager.cancel(run_id)
                break
            if update.text:
                collected_text.append(update.text)
                yield sse_event(update)
    finally:
        await run_manager.finalize(run_id, collected_text)
        # cancelled 时不调用危险的 get_final_response()；按规则写 DB
```

**历史写入策略（关键）**

| Cancel 时机 | 处理 |
|------------|------|
| 纯文本 streaming 中 | 可选保存 partial，`message_type=cancelled`，`metadata.partial=true` |
| tool call 参数未完整 | **不写入** assistant 消息；仅记 audit `run_cancelled` |
| tool 已执行、等待下一轮 model | 保留完整 tool_call + tool_result；不写入半截 assistant 文本 |
| Edit & Resend | 上条 user message 标记 `superseded` 或软删除，写入新 user message |

**三种实践模式**

| 模式 | 历史安全 | 停止速度 | 适用 |
|------|----------|----------|------|
| A. 客户端停展示，服务端跑完 | ⭐⭐⭐ | 慢 | 最简单 |
| B. Task.cancel + 按规则写 partial | ⭐⭐ | 快 | **聊天 Stop 按钮（推荐主路径）** |
| C. Middleware terminate | ⭐⭐⭐ | 中 | ReAct 多轮 tool，阻止下一轮 |
| D. Responses API cancel | ⭐⭐⭐ | 快（服务端） | Background 长任务 |

生产推荐 **B + C 组合**：用户 Stop 走 B；若已在 tool loop 则叠加 C 阻止下一轮 LLM。

**Phase 2 新增 API**

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/runs/{run_id}/cancel` | 取消进行中的 run |
| `GET` | `/api/v1/runs/{run_id}` | 查询 run 状态 |

**Phase 2 新增 DB / 缓存**

```sql
-- 可选：runs 持久化表（亦可仅用 Redis）
CREATE TABLE runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id     UUID NOT NULL REFERENCES chats(id),
    status      VARCHAR(20) NOT NULL,  -- running | completed | cancelled
    response_id VARCHAR(255),          -- Responses API background run 取消用
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at    TIMESTAMPTZ
);
```

`messages.message_type` 扩展：`cancelled`（partial assistant 文本）、`run_cancelled`（审计事件，无 content）。

**Phase 2 新增目录**

```
backend/app/
├── runs/
│   ├── manager.py      # RunManager：创建/取消/_finalize
│   └── middleware.py   # StopRequestedMiddleware
```

**前端（Phase 2）**

- Stop 按钮：`AbortController` + `POST /runs/{id}/cancel`
- 输入框：run `running` 时禁用发送；`cancelled`/`completed` 后立即可用
- 可选：Edit 上条 user message（需 `superseded` 后端支持）

---

### 16.2 A2A Multi-Agent

MAF v1.0 已支持 [A2A 协议](https://learn.microsoft.com/en-us/agent-framework/integrations/a2a)：

```
Agent A (本平台)  ──A2A──▶  Agent B (外部/本平台)
                              │
                              ▼
                         Agent C (专业领域)
```

预留设计：

- `agents.a2a_endpoint` 字段已预留
- API 层 Agent ID 抽象，便于将 Agent 暴露为 A2A Server
- Workflow 编排：sequential / handoff / group chat
- MAF samples 参考：`python/samples/04-hosting/`

---

## 17. 实施路线图

### Phase 1a — 基础骨架（1-2 周）

- [ ] 初始化 `backend/` + `frontend/` 目录结构
- [ ] FastAPI 入口 + `load_dotenv` + 健康检查
- [ ] Alembic 初始化 + 核心表 Migration（users / chats / messages）
- [ ] `ModelRegistry`：GPT 模型连通性验证
- [ ] 单 Agent 非流式 `agent.run()` 端到端

### Phase 1b — 对话与持久化（1-2 周）

- [ ] `PostgresHistoryProvider`（全类型 `load_history_rows` + `to_maf_messages`）
- [ ] `ToolSlimmerRegistry` + `PassthroughToolSlimmer` + `HistoryProjection`（Phase 1 透传）
- [ ] `SessionStore`（Redis 热缓存 + `chats.session_state` 双写）
- [ ] `chat_id` ↔ `AgentSession.session_id` 绑定；`create_session(session_id=chat_id)`
- [ ] `require_per_service_call_history_persistence=True`
- [ ] 流式 SSE + 正常结束时 `get_final_response()` finalize
- [ ] Audit Middleware → messages 表全类型记录
- [ ] agents 表 + CRUD API

### Phase 1c — 能力扩展（2 周）

- [ ] Claude 模型接入（`AnthropicClient`）
- [ ] MCP Registry + 动态挂载（Postgres MCP Server 验证）
- [ ] `SkillsProvider.from_paths()` + `FilteringSkillsSource`
- [ ] Skill 事件审计（skill_load / skill_resource / skill_script）
- [ ] Tool Registry

### Phase 1d — 前端（1-2 周）

- [ ] React 项目初始化
- [ ] AG-UI 流式聊天页面
- [ ] Agent 配置页面
- [ ] Skill 时间线组件
- [ ] **Reasoning 折叠 UI**（`message_type=reasoning` 与 `text` 分轨展示）
- [ ] 对话历史
- [ ] `UtilityModelRegistry` + `ChatTitleService`（首轮后异步标题）

### Phase 1e — 记忆与打磨（1 周）

- [ ] `UserMemoryContextProvider`
- [ ] `HistoryCompactionService`（Utility 模型 `history_compaction`）
- [ ] `CompactionProvider` + `token_budget`（`summarizer_client` 走 Utility 模型）
- [ ] 对话摘要写入 `chats.summary`（摘要时默认剥离 reasoning 正文）
- [ ] OpenTelemetry 基础埋点
- [ ] 错误处理与重试

### Phase 2a — Streaming Cancel / Stop（1-2 周）

- [ ] `RunManager`（Redis run 注册表 + chat 锁）
- [ ] `POST /api/v1/runs/{run_id}/cancel` API
- [ ] SSE 消费循环：disconnect / cancel 检测 + `asyncio.Task.cancel()`
- [ ] `StopRequestedMiddleware`（ReAct tool loop 终止）
- [ ] 历史写入策略：partial / cancelled / superseded 分支逻辑
- [ ] `messages.message_type` 扩展：`cancelled`、`run_cancelled`
- [ ] 前端 Stop 按钮 + `AbortController` + 输入框解锁
- [ ] （可选）Edit & Resend：user message `superseded` 支持
- [ ] （可选）`runs` 持久化表
- [ ] （可选）Responses API background run 服务端 cancel

### Phase 2b — 多 Agent 协作与增强（2-3 周）

- [ ] A2A Server 暴露
- [ ] Workflow 编排 UI
- [ ] RAG 知识库
- [ ] Mem0 集成
- [ ] DeepSeek 模型（Azure Foundry）

---

## 18. 安全与运维

| 项 | 措施 |
|----|------|
| 密钥管理 | `.env` 不入 git；生产用 Azure Key Vault / 环境注入 |
| MCP 隔离 | MCP Server 网络隔离 + 鉴权；stdio 模式限制可执行命令白名单 |
| Skill 脚本 | 沙箱执行（容器/seccomp）+ 超时 + 资源限制 |
| SQL 注入 | ORM（SQLAlchemy）+ 参数化查询 |
| 速率限制 | Redis 令牌桶，按 user_id 限流 |
| 数据合规 | 对话数据按 user_id 隔离；支持删除（GDPR） |
| CORS | FastAPI CORSMiddleware，仅允许 frontend 域名 |

---

## 19. 参考链接

| 资源 | 链接 |
|------|------|
| MAF 官方概览 | https://learn.microsoft.com/en-us/agent-framework/overview/ |
| Agent Skills（渐进式加载） | https://learn.microsoft.com/en-us/agent-framework/agents/skills |
| Skills 官方博客 | https://devblogs.microsoft.com/agent-framework/give-your-agents-domain-expertise-with-agent-skills-in-microsoft-agent-framework/ |
| Agent Skills 开放规范 | https://agentskills.io/ |
| Storage / 自定义 History Provider | https://learn.microsoft.com/en-us/agent-framework/agents/conversations/storage |
| Context Providers | https://learn.microsoft.com/en-us/agent-framework/agents/conversations/context-providers |
| AG-UI 集成 | https://learn.microsoft.com/en-us/agent-framework/integrations/ag-ui/ |
| MCP 集成 | https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/ |
| A2A 协议 | https://learn.microsoft.com/en-us/agent-framework/integrations/a2a |
| GitHub 仓库 | https://github.com/microsoft/agent-framework |
| Python Skills Samples | https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/skills |
| Skills 设计决策文档 | https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0021-agent-skills-design.md |
| Termination & Guardrails | https://learn.microsoft.com/en-us/agent-framework/agents/middleware/termination |
| Background Responses | https://learn.microsoft.com/en-us/agent-framework/agents/background-responses |
| 长任务取消设计（0009） | https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0009-support-long-running-operations.md |
| Stop Streaming 社区讨论 | https://github.com/microsoft/agent-framework/discussions/5548 |
| Multi-Turn 入门 | https://learn.microsoft.com/en-us/agent-framework/get-started/multi-turn |
| Conversations & Memory 概览 | https://learn.microsoft.com/en-us/agent-framework/agents/conversations |
| Context Compaction | https://learn.microsoft.com/en-us/agent-framework/agents/conversations/compaction |
| TextReasoningContent | https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.textreasoningcontent |
| Session 设计（0016） | https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0016-python-context-middleware.md |

---

*本文档将随实施进展持续更新。*
