---
name: proposal-composer
description: >-
  Regional BD/sales proposal desk: maintain proposal_state from MDM catalog (Postgres MCP),
  deterministic pricing, completeness, preview/generate artifacts. Use for BVI incorporation,
  AU advisory, package/SKU changes, pricing facts, required docs, and client proposal output.
---

# Proposal Composer — Skill（对内）

## 与 System Prompt 的分工

| 层 | 位置 | 内容 |
|----|------|------|
| **角色与对外表述** | `system_prompt.md` | 读者是区域 BD/Sales、销售语言、任务驱动、禁止暴露实现细节 |
| **数据与操作内核** | 本文 + `references/*` | state 字段、patch 语义、完整性规则、何时查 catalog |
| **SQL 深挖** | Skill `proposal-mdm-catalog` | 按 keyword / package 展开的查询模板 |

触发本 Skill 后，**用意图驱动操作**，不要对用户复述固定 workflow。

## 核心目标（每轮 implicit checklist）

1. **Proposal state 反映销售已确认的内容**（不是「聊过但没写进 state」）。
2. **价格来自 patch 派生**，不是 LLM 估算。
3. **Completeness 决定是否可 preview / generate**——用来回答「还差什么」，不是用来拒绝改单。

## 意图 → 动作（启发式，非顺序）

| 信号 | 动作 |
|------|------|
| 尚未有 `category_id`，用户已表明 region/BU（如 BVI 注册、AU advisory） | `list_categories` 或直接 `set_category` |
| 用户点了 package 名 / SKU / 「标准注册包」 | SQL 核对 package_id 或 SKU → 确认后 `select_packages` / `selected_skus` |
| 用户给了客户信息 | `set_client`（可与其他 op 同批） |
| 选中 SKU 含 TIERED / `share_count` dimension | 缺则问 share count → `set_pricing_facts` |
| 用户要 optional 块（credentials、appendix、transfer-in 附加说明） | `enable_sections` + 必要时填 `appendix` |
| 销售要改价 | `pricing.overrides` + reason |
| 用户要预览 / draft | `render_preview`（缺 required 且用户坚持 → `draft=true`） |
| 用户要可下载文件 | `generate_document`（仅当 `ready_to_generate` 或用户接受 `force`） |
| 只改客户或只改一股 | 最小 patch，不必重走 catalog |

**合并 patch**：同一轮能确定的字段尽量一次 patch（语义 op 可组合在一次调用里）。

## `proposal_state` 要点

- **可写**：`proposal_meta`、`client`、`pricing_facts`、`selection`、`enabled_sections`、`appendix`、`pricing.overrides`
- **派生（勿 patch）**：`pricing.computed`、`line_items`、`resolved_placeholders`、`peripheral`、`completeness`、`stage`

详见 `references/schema.md`。

## Patch 语义 op（内部参考）

```json
{ "op": "set_category", "category_id": "harneys-bvi" }
{ "op": "set_client", "client": { "company_name": "ABC Ltd", "contact_name": "Jane" } }
{ "op": "select_packages", "package_ids": ["PKG-BVI-INCORP-STD"] }
{ "op": "set_pricing_facts", "pricing_facts": { "share_count": 1 } }
{ "op": "enable_sections", "section_ids": ["additional_info", "credentials"] }
```

也可直接 JSON merge 可写字段；每次 material change 后看 patch 返回或 `get_proposal_state` 里的 `completeness`。

## Catalog 查询（原则）

- 始终 **`category_id` + `status = 'ACTIVE'`**。
- 意图模糊时用 `sku_semantic_for_ai` / `package_semantic_for_ai` / `ILIKE`。
- BVI 政府费：`pricing_type = 'TIERED'`，`price_spec.dimension = 'share_count'`。
- 常用 SQL：`references/bvi-sql.md`、`references/au-sql.md`；复杂探索加载 **`proposal-mdm-catalog`**。

## Required documents

- **不要**读 `knowledge-index.yaml`。
- Patch 选型后看 `resolved_placeholders.knowledge.required_docs` 或 `peripheral.required_docs`，对外转述为销售语言。

## Artifacts

| Tool | 效果 |
|------|------|
| `render_preview` | 聊天内 markdown 预览 widget（可放大） |
| `generate_document` | 落盘 `.md` + 下载 widget |

Blocked 时返回 `missing_required` / `enabled_optional_unfilled`——转成用户能懂的一句话。

## References

- `references/schema.md` — writable vs derived
- `references/bvi-sql.md` — Harneys BVI
- `references/au-sql.md` — AU advisory
