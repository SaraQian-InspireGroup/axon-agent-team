---
name: proposal-composer
description: >-
  Editable proposal_draft semantics: document meta-model (facts, sections by kind),
  preview-vs-draft, patch vs materialize, and template as render contract. Use when
  initializing or editing a proposal draft—not for MDM catalog SQL.
---

# Proposal Composer — Draft Skill

## 与 System Prompt 的分工

| 层 | 内容 |
|----|------|
| **System prompt** | 角色、销售语言、任务驱动 |
| **Tool descriptions** | 各 tool 的调用时机与参数 |
| **本 Skill** | draft **元模型**与编辑原则 |
| **`references/`** | 补充说明（preview 差异、template 字段）；**非**完整 schema 镜像 |

## 编辑原则

1. **Draft 是编辑真相，Preview 是渲染结果** — 改用户指的内容 = 改产生该内容的 draft 字段，不是 panel 上的装饰（编号、分组、脚注序号等）。

2. **先定位，再修改** — `get_proposal_draft` → 按 section `kind` / `id` 找到 node → 用稳定 key（`source.sku`、`package_id`、服务名）定位 → patch。详见 [preview-vs-draft.md](references/preview-vs-draft.md)。

3. **新增 vs 编辑** — catalog 新增用 materializer；可见内容编辑用 patch。勿 patch 手写整行来「加服务」。

4. **Template 是契约** — section 有哪些 slot、render 怎么画，以 `templates/{id}/template.yaml` 为准；结构不清楚时 `read_knowledge` 读 template，不要凭 skill 记路径。

5. **Platform 会重算的不要重复做** — `edit_state: source` 的块、add_package 触发的 narratives/占位符；只为销售明确要的差异 patch，必要时锁定 edit_state。

6. **改完核对 draft** — 右侧面板随 draft 更新；报价以 draft fee rows 为准。

7. **Readiness 只约束导出** — live preview / 改单无步骤锁。

## Document 元模型

```
proposal_draft
├── meta          … template_id, title
├── facts         … client, inputs（跨 section 的事实）
└── document
    └── sections[]   … 每个 node 有 kind，kind 决定「里面有什么」
```

**不要**把 skill 当成 JSON Schema 镜像。对象演进时：**以 `get_proposal_draft` 返回为准**；本 skill 只描述稳定 **概念层**。

### Section 由 `kind` 决定形状

| kind | 概念 | 典型可编辑内容 |
|------|------|----------------|
| `markdown_block` / `static_block` | 单块文案 | `content`（视 editable） |
| **`fee_section`** | **定价区 composite**（见下） | intro、package 叙事、fee rows |
| `derived_section` | 从其他 draft 推导 | 启用/配置；一般不 patch 生成结果 |
| `collection` | 条目列表 | `items[]` |

其他 kind 出现时：读 template + 当前 draft，按 node 上实际字段编辑。

### `fee_section`：一个 section，多个内容槽

Template 里通常一个 id（如 `solution_and_fees`）对应 **一个** `fee_section` node，**不是**两个并列 template section。

Draft 内按 **语义槽** 组织（非独立 sub-section id）：

| 槽 | 存什么 | Preview 里大致对应 |
|----|--------|-------------------|
| `intro` | 定价区引导文案 | Solution 开头段落 |
| `narratives[]` | 每个 package 的 solution 叙事块 | package 说明段落（在 fee 表 **之前**） |
| `tables[].rows[]` | 计费行（SKU、展示字段、price、footnotes 等） | Fee tables（在叙事 **之后**） |

**Preview 顺序**（intro → narratives → fee 表标题 → tables → 可选脚注区）由 platform render + `fee_layout` 决定，不是 draft 里再嵌一层 section tree。

`add_package` 同时往 `narratives[]` 和 `tables[]` 写入；改 package 叙事 patch narrative 的 `content`，改价 patch 对应 row 的 price 字段。

### Row 级字段：按语义找，不按 jurisdiction 记路径

Fee row 是 **结构化业务对象**，常见语义类别：

| 类别 | 含义 | patch 场景 |
|------|------|------------|
| **identity / provenance** | `source.sku`, `source.package_id`, `id` | 定位用，少改 |
| **display text** | `service_name`, `description`, `scope_of_work` | 销售改展示、SOW |
| **pricing** | `price.amount`, `price.fee_raw`, `pricing_type` | 改总价 / 规则文案 |
| **footnotes** | `footnotes`（行级文本） | 改脚注 **正文** |

JSON Pointer 模式：`/document/sections/{i}/…`，其中 `{i}` 下具体 key 名 **以 draft 为准**（如 `tables/{t}/rows/{r}/footnotes`）。不必 memorized 每张表的路径。

### `fee_layout`：只改显示，不改存储路径

`fee_layout`（在 fee_section 或 template 上）控制 **怎么画**，不改变 footnote/price 存在哪：

| layout 开关 | 存储 | Preview |
|-------------|------|---------|
| `footnotes: aggregate` | 仍在 **每行** `rows[].footnotes` | 全文去重、统一编号、section 末一次渲染 |
| `group_by: department` | rows 仍在 tables 内 | render 时按 `department_team` 拆多张表 |
| `service_columns` | 各字段仍在 row 上 | 决定 Service 单元格展示哪些列 |
| `table_style` | — | 是否显示 `2.2` 行号等 |

未来非 aggregate 脚注模式：row 路径仍相同，仅 render 不同。

### Facts 与 placeholders

`facts.client` / `facts.inputs` 是跨 section 输入；template `placeholders` 在 render 时注入 markdown 块。Patch client facts 即可；勿为 `{{client.*}}` 去 patch introduction 全文（除非销售要 override 且 edit_state 允许）。

## 用户指称 → 思考方式

- **某行 / 某价 / SOW / 脚注** → 在 `fee_section` 的 `tables[].rows[]` 里按 sku/名称定位 → patch 对应 **语义字段**。
- **某 package 方案说明** → `narratives[]` 里按 `package_id` 定位 → patch `content`。
- **客户 / 公司** → `facts.client.*`。
- **其他章节** → `sections[]` 里按 `id` + `kind`。
- **加/换 catalog 项** → catalog 查询 → materialize；只改已有 draft → patch。

Path 不确定：**读 draft**，不要猜数组下标。

## References

| 主题 | Resource |
|------|----------|
| Preview vs draft、指称解析 | [preview-vs-draft.md](references/preview-vs-draft.md) |
| Template 字段与 section kind | [template-contract.md](references/template-contract.md) |
| 补充字段说明（非权威 schema） | [schema.md](references/schema.md) |

Template：`read_knowledge("templates/{template_id}/template.yaml")`。
