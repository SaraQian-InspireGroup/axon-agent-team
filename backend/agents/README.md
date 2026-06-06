# Agent definitions (file-based)

Each subdirectory under `backend/agents/` is one deployable agent. The platform loads these on startup — no UI configuration.

## Layout

```
agents/
  <slug>/
    profile.yaml
    system_prompt.md
    mcp_servers.yaml      # optional
    skills/<name>/SKILL.md
```

`profile.yaml` 的 `id` 必须与目录名一致。

## profile.yaml

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Slug，与目录名一致 |
| `name` | yes | 显示名 |
| `model_provider` | yes | `azure_openai` / `azure_anthropic` |
| `model` | yes | Deployment；支持 `${ENV_VAR}` |
| `mcp_servers` | no | 本 agent `mcp_servers.yaml` 中的 key |
| `allowed_tools` | no | MAF 工具名，如 `postgres_query_data`（对应 mcp-postgres 的 `query_data`） |
| `hooks` | no | 平台 hook 及参数（见下） |

### hooks（平台可复用）

Hook 实现注册在 `app/platform/hook_catalog.py`，任意 agent 按名称启用并覆盖参数：

```yaml
hooks:
  sql_validator:
    max_rows: 2000
  result_truncator:
    max_observation_bytes: 50000
```

仅用默认值时可写 `sql_validator: {}` 或列表形式 `- sql_validator`。

| Hook | 参数 | 默认 |
|------|------|------|
| `sql_validator` | `max_rows` | `2000` |
| `result_truncator` | `max_observation_bytes` | `50000` |

新增平台 hook：在 `hook_catalog.py` 注册 `HookSpec`，各 agent 的 profile 即可引用。

### 完整示例

```yaml
id: odi-analysis
name: "ODI Knowledge AI Chat Analysis Agent"
model_provider: azure_anthropic
model: ${CLAUDE_AZURE_FOUNDRY_MODEL}

mcp_servers:
  - postgres

allowed_tools:
  - postgres_list_tables
  - postgres_describe_table
  - postgres_get_schema
  - postgres_query_data

hooks:
  sql_validator:
    max_rows: 2000
  result_truncator:
    max_observation_bytes: 50000
```

## Adding an agent

1. `backend/agents/<slug>/` + `profile.yaml` + `system_prompt.md`
2. 按需添加 `mcp_servers.yaml`、`skills/`
3. 重启后端
