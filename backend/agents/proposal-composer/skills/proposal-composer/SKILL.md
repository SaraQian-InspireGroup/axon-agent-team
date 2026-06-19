---
name: proposal-composer
description: >-
  Domain rules for the Proposal Composer agent: editable proposal_draft semantics,
  template section contracts, draft fee rows, optional/derived sections, and
  proposal generation workflow.
---

# Proposal Composer — Skill（对内）

## 与 Tool Description / System Prompt 的分工

| 层 | 写什么 | 不写什么 |
|----|--------|----------|
| **Tool descriptions** | 何时调哪个 tool、JSON Patch / path 语义 | 销售话术、jurisdiction 业务 |
| **System prompt** | 角色、对外语言、任务驱动节奏 | 重复 tool 路由表 |
| **本 Skill** | 业务意图、draft 字段、完整性怎么解读 | 再写一遍 tool description / MDM SQL |
| **`references/schema.md`** | Draft JSON Pointer / JSON Patch 路径示例 | — |
| **`proposal-mdm-catalog`** | MDM schema-first SQL / catalog few-shot | draft patch 语义 |

**Tool 怎么选**：读各 builtin / MCP tool 的 description；本 Skill 只补充 **填什么、查什么、怎么验证**。

## 核心目标（每轮 implicit checklist）

1. **Draft 是展示草稿**——用户看到什么就改 draft 的对应 node。
2. **Catalog additions 走 materializer**——新增 MDM package/service 先用 MCP SQL 查询，再把返回行传给 add tools，让平台生成 fee table/row 与 source/provenance；不要手写完整 fee row。
3. **展示编辑走 patch**——客户信息、section content、table title、fee row `service_name` / `scope_of_work` / `price.amount`（汇总金额）/ `price.fee_raw`（非 FIXED 展示文案）用 JSON Patch。
4. **选型后检查 draft fee tables**——添加 package/service 后读 draft 的 `fee_section.tables[].rows[]`，确认右侧展示对象真的更新。
5. **Readiness 只影响导出**——缺项可继续 draft/preview；正式下载看 `generate_document` 返回的 ready/block 状态。
6. **写 draft tools 不并发**——会修改 draft 的工具顺序调用；多个服务一次放进 `services` array。

## 业务意图 → 做什么（非 tool 清单）

| 销售信号 | 你要完成的 |
|----------|------------|
| 刚明确 jurisdiction/BU，尚未定 template | 对齐可用 `template_id` |
| **template_id 刚设定** | `initialize_proposal_draft(template_id)`；必要时读 `templates/{id}/template.yaml` |
| 口头点了方案名 / SKU，ID 不确定 | 加载 **`proposal-mdm-catalog`**：`describe_table` → SQL 查 `package_id` / `sku` |
| **追加**服务（保留已有 fee rows） | 先用 MCP SQL 查 service rows，再 `add_services_to_proposal_draft`，参数是 `{"services":[{...}]}` |
| **添加 package** | 先用 MCP SQL 查 package row + service rows，再 `add_package_to_proposal_draft`，参数是 `{"package":{...},"services":[{...}]}` |
| 给了客户名、简称、地址、联系人等 | patch draft `/facts/client/*`；`company_name`、`short_name`、`address`、`contract_name`、`contract_title`、`contract_email` 是 optional facts |
| 要 credentials / appendix / payment summary 等块 | patch draft section 或用 `enable_proposal_draft_section` 启用；AU payment options 是 `payment_options` derived section，多报价方式写入该 section 的 `options` |
| 销售要改某一行的价 | patch draft fee row `price.amount`（汇总 total）；非 FIXED 行 fee table 展示仍来自 `price.fee_raw`，必要时也可 patch `price.fee_raw` |
| 销售要改某一行的显示标题 / SOW | patch draft fee row `service_name` / `scope_of_work` |
| 用户要看 proposal | **不必**为右侧面板反复 preview——patch 后面板 live 更新；口头总结前用 draft fee tables/rows 核对 |
| 用户要 **下载/发客户** 正式文件 | `generate_document`；若 blocked，补缺口或经用户同意后 `force` |

**合并 patch**：同一轮能确定的字段尽量一次写入；新增不存在字段用 JSON Patch `add`，已存在字段才用 `replace`，不确定路径先 `get_proposal_draft`。

## Draft 与文档

- 字段与路径：**`get_proposal_draft`** 或 **`references/schema.md`**
- **模版契约（section kind、optional、derived、列/hints）**：**`read_knowledge("templates/{template_id}/template.yaml")`** — 见 **`references/template-contract.md`**
- Patch 后核对：draft `/document/sections` 中对应 section/table/row（对外翻译成白话）
- **Live 面板**：平台按 draft 渲染 proposal 正文；聊天内 artifact 仅 **generate** 等里程碑

## Catalog 边界

MDM 查询统一加载 **`proposal-mdm-catalog`**。本 core skill 只负责把已确认的 MDM rows 写入 draft，并在写入后核对 fee tables/rows。

## References

- `references/schema.md` — draft JSON Pointer / Patch 常用路径
- `references/template-contract.md` — **何时/如何读 `template.yaml`**、section 类型、与 draft materialization 的配合
