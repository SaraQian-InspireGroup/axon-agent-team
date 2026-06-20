# Template Contract (`template.yaml`)

## 它是什么

每个 `template_id` 在 `knowledge/templates/{template_id}/template.yaml` 定义：

- draft **materialize** 时有哪些 section、默认是否启用；
- 各 section 的 **kind** 与可编辑性；
- **fee_layout**、**placeholders**、**derivation** 等 render 规则。

Platform 与 agent 共用同一文件：platform 据此生成 draft 和 preview；agent patch 须与之一致。

```text
read_knowledge("templates/{template_id}/template.yaml")
```

`/meta/template_id` 来自 draft；未定 template 时用 `list_templates`。

## 何时需要读

**原则**：当你需要理解 **「这个 section 在 draft 里长什么样 / preview 为何这样画」** 时读 template — 不是按场景 checklist，而是 **认知不足时查契约**。

典型触发：新 template、 unfamiliar section kind、fee 表分组/列/脚注行为、derived section、optional 块是否可 patch。

小 patch 且本 session 已理解该 template 结构时，可不重复读。

Catalog 价格与 SKU 不在 template 里 — 走 Postgres MCP。

## Section kind → draft 行为

| kind | Draft 形态 | Agent 通常做什么 |
|------|------------|------------------|
| `static_block` | 来自 `blocks/*.md`；多不可编辑 | 一般不 patch |
| `markdown_block` | `content` + `edit_state` | patch `content` |
| `fee_section` | `intro`、`narratives[]`、`tables[]` | materialize rows；patch 行字段/叙事 |
| `collection` | 结构化条目列表 | patch 条目 |
| `derived_section` | platform 从其他 draft 节点推导 | `enable_proposal_draft_section`；勿改生成内容 |

## `template.yaml` 字段速查

| 区域 | 含义 |
|------|------|
| `sections[].id` | 稳定 id；`enable_proposal_draft_section` 与定位用 |
| `sections[].kind` | 见上表 |
| `sections[].default_enabled` / `required` | 初始可见性 / 能否关闭 |
| `sections[].editable` | 是否允许 patch 可见内容 |
| `sections[].source` / `intro.source` | 初始内容来源 |
| `sections[].fee_layout` | 表样式、列、分组、脚注、列宽等 render 规则 |
| `sections[].package_narratives.index` | package_id → narrative 模板路径（materialize 进 `narratives[]`） |
| `placeholders` | introduction 等处的令牌解析规则 |
| `sections[].derivation` | 如 AU `payment_options_from_fee_tables` |
| `document_title` | `meta.title` 构建规则 |

静态正文在 `blocks/*.md`；结构规则在 `template.yaml`。

## 与 edit_state 的关系

Section / narrative 的 `edit_state.content`（及类似字段）区分 **platform 可重算（source）** 与 **人工锁定（manual/custom）**。patch 销售定制文案后，若不应再被 placeholder 覆盖，需理解当前节点的 edit_state 语义再决定是否一并调整。
