# Proposal Draft — Supplementary Reference

**权威形状**：运行时 **`get_proposal_draft`** 返回的 JSON。本文件是概念补充，**不是**需随每次模型变更同步的路径清单。

元模型与编辑原则见主 Skill **Document 元模型**。

## 三层结构

| 层 | 角色 |
|----|------|
| `meta` | 哪份 template、文档标题 |
| `facts` | 客户与定价输入（跨 section） |
| `document.sections[]` | 按 template 物化的章节；**`kind` 决定 node 形状** |

定位 section：`sections[].id` + `sections[].kind`（fee 区通常是 `kind: fee_section`）。

## `fee_section` 内容槽（非 template 子 section）

一个 `fee_section` node 内：

```
intro          … 可选引导文案
narratives[]   … package 叙事（kind: package_narrative）
tables[]       … fee_table → rows[]（kind: fee_row）
fee_layout     … render 规则（也可由 template 合并）
```

Preview 顺序由 platform render 决定（通常 narratives 先于 fee tables），不是 draft 里再嵌 `sections[]`。

## Fee row：语义字段（非穷举路径）

Patch 时按 **语义** 找 field，路径形如 `/document/sections/{si}/tables/{ti}/rows/{ri}/{field}`：

| 语义 | 常见 field | 备注 |
|------|------------|------|
| 定位 | `source.sku`, `source.package_id`, `id` | 优先用于匹配用户指称 |
| 展示 | `service_name`, `description`, `scope_of_work` | 取决于 `service_columns` 是否在 preview 显示 |
| 定价 | `price.amount`, `price.fee_raw`, `price.pricing_type` | 汇总用 amount；非 FIXED 展示常看 fee_raw |
| 脚注 | `footnotes` | **始终在行上**；见下 |

`edit_state` 标记字段是否仍跟 MDM/template source 同步。

## Footnotes：存储 vs aggregate 显示

| | Draft | Preview（BVI `footnotes: aggregate`） |
|---|-------|----------------------------------------|
| 存哪 | 每行 `rows[].footnotes`（字符串） | — |
| 怎么画 | — | 相同文案去重；`<sup>` 链到 section 末 `<ol>` |
| 怎么改 | patch 该行的 `footnotes` | 不要 patch preview 底部 HTML 或虚构 section 级 footnotes 数组 |

其他 region 若将来不用 aggregate：row 路径 **不变**，仅 render 布局不同（例如每表脚注、行内脚注）。以 template `fee_layout.footnotes` + 当前 preview 为准。

## Pricing display（render 语义）

- `FIXED` → 表内展示格式化 `price.amount`
- 其他 `pricing_type` → 常展示 `fee_raw` 规则文案；Total/汇总仍看 `price.amount`
- `group_by` / `column_widths` / `table_style` → 只影响 layout，不改变 row 字段集合

## Patch 示例（illustrative）

```json
[
  {"op": "replace", "path": "/facts/client/company_name", "value": "Acme Ltd"},
  {"op": "replace", "path": "/document/sections/2/tables/0/rows/1/price/amount", "value": 1200}
]
```

Section/row 索引 **0-based**，且须与 **当前 draft** 一致。Catalog 新增用 materializer，勿手写 row。

## Readiness

Incomplete draft 仍可 preview；`generate_document` 检查 completeness。
