---
name: proposal-composer
description: >-
  Editable proposal_draft semantics: document meta-model (facts, sections by kind),
  preview-vs-draft, patch vs materialize, and template as render contract. Use when
  initializing or editing a proposal draft—not for MDM catalog lookup (see proposal-mdm-catalog skill).
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

4. **Template 是契约** — section 有哪些 slot、render 怎么画，以 `templates/{id}/template.yaml` 为准（`read_knowledge("templates/{template_id}/template.yaml")`，`template_id` 来自 `/meta/template_id`）。结构不清楚时查契约，不要凭 skill 记路径。常用字段：

   | 字段 | 含义 |
   |------|------|
   | `sections[].id` / `kind` | 稳定 id；kind 决定 node 形状（见上表） |
   | `sections[].default_enabled` / `required` | 初始可见性 / 能否关闭 |
   | `sections[].editable` | 是否允许 patch 可见内容 |
   | `sections[].fee_layout` | 表样式、列、分组、脚注、列宽等 render 规则 |
   | `sections[].package_narratives.index` | package_id → narrative 模板路径 |
   | `sections[].derivation` | `derived_section` 专用：`type`、`source_section`；决定推导与配置语义 |
   | `placeholders` | introduction 等处的占位符解析规则 |

   静态正文在 `blocks/*.md`；结构规则在 `template.yaml`。Catalog 价格与 SKU 不在 template 里。

5. **Platform 会重算的不要重复做** — `edit_state: source` 的块、add_package 触发的 narratives/占位符；只为销售明确要的差异 patch，必要时锁定 edit_state。patch 销售定制文案后，若不应再被 placeholder 覆盖，确认该 node 的 edit_state 语义再决定是否一并调整。

6. **Readiness 只约束导出** — live preview / 改单无步骤锁。

## Reply gate（回复前强制检视）

**何时必须做**：本轮调用了 **任何会改 draft 的 tool**，或你准备在回复里 **声称** 某内容「已加入 / 已改 / 已启用 / 已完成」时。纯 catalog 问答、用户尚未确认写 draft 时可跳过。

**目的**：避免「tool 调了 ≠ 用户意图已满足 ≠ 回复里说的属实」——例如只 `enable` 推导型 section 却对用户说两套方案都已写好。

**做法（泛化，非场景 checklist）**：

1. **收束用户意图** — 本句 + 仍有效的先前要求：要哪些 section / package / 服务 / 变体 / 客户字段 / 价格？
2. **读 draft 真相** — 优先用 **最后一笔写 draft tool 返回的 `draft`**；不够再 `get_proposal_draft`（或 `path` 查相关 subtree）。**不要**仅凭 tool 成功或自己的计划下结论。
3. **三维对照**（逐条问，不限于 fee / payment）：
   - **Scope**：用户要的每一块在 draft 里是否 **存在且 enabled**（含 derived 的配置是否够，不是只有 default）？
   - **Fidelity**：名称、SKU、金额、optional 内容是否与用户指定一致（报价仍看 fee rows 的 `price.amount`）？
   - **Honesty**：准备写的回复，是否 **每一条完成态表述** 都能在上一步 draft 里找到依据？说不清就改 draft 或改口（部分完成 / 还差什么）。
4. **推导 / 聚合 render** — 若意图涉及 `derived_section`、footnote 聚合、分组表等，draft 字段对了仍可能和 panel 不一致时，再 `render_preview` 或让用户看 panel；**panel 与 draft 冲突以 draft 为准去 patch**。
5. **Fail closed** — 对不上：**继续 patch / enable / materialize**，或 **明确告知未完成项**；禁止「Done + 右侧面板将会显示…」式空头承诺。

与 **generate 门禁** 无关：Reply gate 约束 **你对销售的每一句完成态表述**；`ready_to_generate` 仍只约束导出。

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
| `derived_section` | 从其他 draft 节点 **render 时推导** | 见下 **推导型 section** |
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

### `derived_section`：推导型 section

**概念**：Preview 里该 section 的正文 **由 platform 按 `derivation` 规则从其他 draft 节点渲染时计算**，agent 不写也不应 replace 其 markdown 内容。Draft 上存的是 **开关 + 推导所需配置**，不是最终渲染结果。

**核心认知**：`enable_proposal_draft_section` 只切换可见性；**enable ≠ 用户意图已满足**。platform 在配置缺失时只应用该 `derivation.type` 的内置 default，default 往往是最简结果（例如单套汇总）。用户要的变体、多套方案、alternate 配置——这些需要在 enable 之后 **额外 patch 该 section 的配置字段**。

**workflow（适用所有 `derived_section`，无论 template）**：

1. **发现** — 读 template（`read_knowledge("templates/{id}/template.yaml")`），找到 `kind: derived_section` 的 node；注意 `derivation.type`、`derivation.source_section`、`default_enabled`，以及 **`derivation.agent_guidance`**（若存在，里面有 default_behavior、config_slots、格式说明和示例）。**不要凭 skill 记哪个 template 有哪些 derived_section**——template 会增加，skill 不跟实例走。
2. **读配置现状** — `get_proposal_draft` 定位该 node；看 **该 node 上实际有哪些配置字段**（以返回 JSON 为准，不猜 schema）。
3. **Enable** — 若 `default_enabled: false`，先 `enable_proposal_draft_section`。停在这里，**不要向用户宣称已完成**。
4. **判断 default 是否够用** — 对照用户意图与 default 推导结果：够用则止，不够则继续。
5. **Patch 配置** — 用户要超出 default 的变体/配置时，`patch_proposal_draft` 写入该 section 的配置 slot。**配置格式以 template.yaml 里 `derivation.agent_guidance.config_slots` 为准**（platform 读 `type`/`source_section`，`agent_guidance` 只给 agent 看）。**不要发明字段**——只用 template 文档里出现的 key 和结构。
6. **Reply gate** — 在回复之前，Scope 维逐条确认用户指名的每个变体在 draft 配置里都存在（见 Reply gate）。

**勿 patch 生成结果** — `policy.editable: false` 时不要 replace 渲染出的 markdown；改 **配置 slot** 或 `intro.content`（若 template 标记 editable）。

**与普通 optional section 的本质区别**：普通 optional（`markdown_block`、`collection` 等）enable 之后即显示已有内容，用户要改就改内容字段；`derived_section` enable 后内容来自推导，用户要「第二套方案」类需求时 **enable 不够，必须 patch 推导配置**。同一个 tool `enable_proposal_draft_section`，两类语义不同——遇到 `derived_section` 必须额外问：**default 推导是否已覆盖用户的全部意图？**

*例*：au-advisory `payment_options`（`payment_options_from_fee_tables`）默认推导单套汇总方案；用户要月付 Option B 时 enable 不够，需 patch 该 node 的配置字段（字段名从 `get_proposal_draft` 读，不从 skill 查表）。

### Facts 与 placeholders

`facts.client` / `facts.inputs` 是跨 section 输入；template `placeholders` 在 render 时注入 markdown 块。Patch client facts 即可；勿为 `{{client.*}}` 去 patch introduction 全文（除非销售要 override 且 edit_state 允许）。

## 用户指称 → 思考方式

- **某行 / 某价 / SOW / 脚注** → 在 `fee_section` 的 `tables[].rows[]` 里按 sku/名称定位 → patch 对应 **语义字段**。
- **某 package 方案说明** → `narratives[]` 里按 `package_id` 定位 → patch `content`。
- **客户 / 公司** → `facts.client.*`。
- **`derived_section`**（需要 enable 的推导型章节）→ 先读 template 确认 `derivation.type`；enable ≠ 全部变体；读 draft 发现配置字段 → patch。
- **其他 optional 章节**（`markdown_block`、`static_block`、`collection` 等）→ enable 后 patch 该 kind 的内容字段（`content`、`items[]`…）。
- **加/换 catalog 项** → catalog 查询 → materialize；只改已有 draft → patch。

Path 不确定：**读 draft**，不要猜数组下标。

## References

| 主题 | Resource |
|------|----------|
| Preview vs draft、指称解析 | [preview-vs-draft.md](references/preview-vs-draft.md) |
