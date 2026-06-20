# Preview vs Draft

## 本质关系

```
proposal_draft  +  template.yaml (fee_layout, placeholders, section kinds)
        ↓
   render (platform)
        ↓
   Proposal Preview（右侧面板）
```

- **Draft**：可编辑、可持久化的结构化文档。
- **Preview**：只读视图；含 **render 层** 才出现的排版、编号、分组、占位符展开、footnote 聚合等。

**原则**：用户指向 panel 上的任何内容，你要改的是 draft 里 **生成该内容** 的字段，不是 panel 上的 HTML 或装饰性前缀。

## Render 层常见现象（不是 draft 字段）

| Preview 里可能有 | Draft 里实际存什么 |
|------------------|-------------------|
| 表序号 `### 2. Title`、行前缀 `2.2 Service Name` | `tables[].title`、`rows[].service_name`（**无** 编号前缀） |
| 按 department 拆成多张表 | 同一张 logical table 的 rows，`department_team` 字段 |
| `{{client.*}}`、package bullet list | `facts.client`、`fee tables` / placeholders 规则 |
| 脚注 `[1]` 与文末汇总 | `rows[].footnotes`；聚合编号由 `fee_layout.footnotes` 决定 |
| SOW 渲染成 HTML 列表 | `rows[].scope_of_work` 纯文本 |

具体规则因 template 的 `fee_layout.table_style`、`group_by`、`service_columns` 而异 — 必要时读 `template.yaml`，不要假设所有 jurisdiction 同一套编号。

## 解析用户指称

用户可能用：panel 编号、表名、服务名、SKU、SOW 片段、「那一行」等。通用思路：

1. **读 draft**（`get_proposal_draft`），找到 `fee_section` 或相关 section。
2. **若指称含 render 序号**（如「2.2」「第二张表第三行」）：
   - 记住：序号是 **有内容的表/行** 在 preview 中的 **1-based 显示序**，不是 JSON 的 0-based 下标。
   - 空表在 draft 数组里可能占位，但 preview 计数时常 **跳过空表**。
   - 结合 template 的 `fee_layout` 判断当前 template 是否 **在行上显示** `{table}.{row}` 前缀（有的 layout 只显示服务名）。
3. **优先用稳定 key 定位**：`rows[].source.sku` > `rows[].id` > `service_name` / `description` + `tables[].title`。
4. **定位到唯一 row 后**，patch 该 row 上的目标字段（`scope_of_work`、`price.amount`、`service_name` 等）。
5. **仍歧义** → 用 **一个问题** 确认（SKU 或服务名即可），不要报 JSON 路径给用户。

## 常见思维错误

| 错误假设 | 为何错 |
|----------|--------|
| Panel「2.2」= `rows[2]` | 显示序 1-based；前缀里的 2 是 **表** 序号不是 row 下标 |
| 「2.2」= 全 proposal 第 2 行 | 通常是 **第 2 张（非空）fee 表** 的第 2 行 |
| `service_name` 里含「2.2」 | 编号是 render 时加的 |
| Catalog / MDM 顺序 = draft row 顺序 | Draft 顺序 = materialize / add 顺序 |
| 改 preview 里看到的 HTML | 应改 draft 源字段（如 `scope_of_work` 文本） |

## 与 patch 的关系

JSON Pointer 用的是 draft 数组的 **物理下标**（0-based）。从用户指称到 pointer 的映射是 **推理问题**，不是固定公式；`get_proposal_draft` + template 理解 + 上表原则即可，无需 memorized 映射表。
