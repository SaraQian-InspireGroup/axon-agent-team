---
name: proposal-composer
description: >-
  Regional BD/sales proposal desk: domain rules for proposal_state, MDM catalog context,
  completeness, and region-specific SQL. Load for BVI/AU quoting, package/SKU selection logic,
  pricing facts, required docs, and document content—not for basic tool routing (see tool descriptions).
---

# Proposal Composer — Skill（对内）

## 与 Tool Description / System Prompt 的分工

| 层 | 写什么 | 不写什么 |
|----|--------|----------|
| **Tool descriptions** | 何时调哪个 tool、JSON Patch / path 语义 | 销售话术、region 业务 |
| **System prompt** | 角色、对外语言、任务驱动节奏 | 重复 tool 路由表 |
| **本 Skill** | 业务意图、state 字段、SQL 范式、完整性怎么解读 | 再写一遍「何时 list_categories / get_state」 |
| **`references/schema.md`** | JSON Patch 路径示例 | — |
| **`proposal-mdm-catalog`** | 探索型 SQL 模板 | 已选型后的改单 |

**Tool 怎么选**：读各 builtin / MCP tool 的 description；本 Skill 只补充 **填什么、查什么、怎么验证**。

## 核心目标（每轮 implicit checklist）

1. **State 反映销售已确认的内容**——聊过但未 patch 的不算数。
2. **价格来自 patch 派生**——禁止心算或口头改价（override 须进 `pricing.overrides` 并说明原因）。
3. **Completeness 用来回答「还差什么」**——不用来拒绝改单；缺项可 draft，正式下载看 `ready_to_generate`。

## 业务意图 → 做什么（非 tool 清单）

| 销售信号 | 你要完成的 |
|----------|------------|
| 刚明确 region/BU，尚未定 category | 对齐 `category_id`（必要时查 categories 表意，不写 SQL 教程） |
| 口头点了方案名 / SKU，ID 不确定 | 加载 **`proposal-mdm-catalog`** 或 `references/*-sql.md` 核对后再写入 selection |
| **追加**服务（保留已有 line） | `add` 到 `/selection/selected_skus/-` |
| **替换**整单服务清单 | `replace` `/selection/selected_skus` 为完整列表 |
| 给了客户名、联系人、股数等 | 写入 `client` / `pricing_facts`（TIERED 政府费缺 share count 才问） |
| 要 credentials / appendix / payment summary 等块 | `enabled_sections` + 必要时 `appendix` / `payment_options` |
| 销售要改某一行的价 | `pricing.overrides` + reason |
| 用户要看 proposal | **不必**为右侧面板反复 preview——patch 后面板 live 更新；口头总结前用 `line_items` / patch 返回值核对 |
| 用户要 **下载/发客户** 正式文件 | 满足 completeness 或经用户同意 `force` 后 generate |

**合并 patch**：同一轮能确定的字段尽量一次写入。

## State 与文档

- 字段与路径：**`get_proposal_schema`** 或 **`references/schema.md`**
- Patch 后核对：`/line_items`、`/completeness`（对外翻译成白话）
- **Required docs**：选型后看 `peripheral.required_docs` / placeholder 解析结果；**不要**手读 `knowledge-index.yaml`
- **Live 面板**：平台按 state 渲染 proposal 正文；聊天内 artifact 仅 **generate** 等里程碑

## Catalog（本 Skill 保留的部分）

- SQL 仅 SELECT；scope = 当前 `category_id` + `status = 'ACTIVE'`
- 意图模糊：`sku_semantic_for_ai` / `package_semantic_for_ai` / `ILIKE`
- BVI 政府费：`pricing_type = 'TIERED'`，`price_spec.dimension = 'share_count'`
- 常用片段：`references/bvi-sql.md`、`references/au-sql.md`；深度探索 → **`proposal-mdm-catalog`**

## References

- `references/schema.md` — writable vs derived、completeness 字段
- `references/bvi-sql.md` — Harneys BVI
- `references/au-sql.md` — AU advisory
