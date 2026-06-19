---
name: proposal-mdm-catalog
description: >-
  Read-only MDM SQL when package_id/SKU needs lookup. Always describe_table/get_schema on
  mdm_services before writing SQL; use few-shots in this skill. Not for post-selection patches.
---

# Proposal MDM Catalog — Skill（对内）

**何时加载**：销售说的方案还不对应具体 `package_id` / SKU，或需要 **对比 package、按关键词搜服务、看 package 含哪些 SKU**。

**何时不必加载**：用户已明确 package/SKU 且你要做的是 **改单、增删服务、改客户**——直接 patch（tool description）；不要为改单反复 SQL。

## 写 SQL 前必做（schema-first）

**禁止**凭记忆或臆造列名直接 `query_data`（常见错误：写 `price_note`——**该列不存在**）。

按顺序：

1. **`postgres_describe_table`**（或 **`postgres_get_schema`**）确认 `mdm_services` / `mdm_packages` / `mdm_package_services` 的列名。
2. 只 SELECT 上一步看到的列；
3. **`postgres_query_data`**（`query` 参数必填、非空 SELECT）；scope 带 **`category_id`** + **`status = 'ACTIVE'`**。
4. 用销售语言总结；**确认后再** 用 `add_package_to_proposal_draft` / `add_service_to_proposal_draft` 写入 draft fee section。

`mdm_services` 常用列（以 describe 结果为准）：

| 列 | 用途 |
|----|------|
| `sku`, `category_id`, `status` | 过滤 |
| `service_name_on_proposal`, `scope_of_work`, `sku_semantic_for_ai` | 展示 / 搜索 |
| `service_group`, `department_team` | 分组 |
| `pricing_type`, `price_amount`, `price_min`, `price_max`, `price_currency` | 定价 |
| `price_spec` | TIERED / MATRIX 等（JSONB） |
| `fee_raw`, `footnotes` | 费用说明文字 |
| `billing_frequency`, `recurring` | 周期 |

**不存在**：`price_note`、`price_notes` 等——勿使用。

## 原则

- 只读 SELECT；`category_id` + `status = 'ACTIVE'`。
- Package ↔ SKU 的 JOIN 必须带 **`ps.category_id = s.category_id`**（及 `ps.sku = s.sku`）。
- SQL 里的 `price_amount` 仅作推荐；对外报价以 draft fee rows 为准。

## Few-shot 工作流

### 1）首次查 AU catalog（推荐顺序）

```
→ postgres_describe_table("mdm_services")
→ postgres_query_data: 列出 package（见 au-sql.md）
→ postgres_query_data: 按关键词或 package_id 查 SKU
→ 向用户确认 package/SKU
→ add_package_to_proposal_draft / add_service_to_proposal_draft
```

### 2）已知 package_id，查包含哪些服务

```sql
SELECT ps.package_id, ps.sku,
       s.service_name_on_proposal, s.pricing_type,
       s.price_amount, s.fee_raw, s.footnotes, s.price_spec
FROM mdm_package_services ps
JOIN mdm_services s
  ON ps.sku = s.sku AND ps.category_id = s.category_id
WHERE ps.category_id = 'au-services'
  AND ps.package_id = 'PKG-AU-EXAMPLE'
  AND s.status = 'ACTIVE'
ORDER BY ps.sku;
```

### 3）销售口述「incorporation / tax / payroll」— 关键词搜 SKU

```sql
SELECT sku, department_team, service_name_on_proposal,
       pricing_type, price_amount, price_spec
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku NOT LIKE 'ADT%'
  AND (
    service_name_on_proposal ILIKE '%payroll%'
    OR sku_semantic_for_ai ILIKE '%payroll%'
  )
ORDER BY department_team, sku;
```

### 4）用户给了多个 SKU 代码 — 批量核对（SKU 必须来自 catalog，勿编造）

```sql
SELECT sku, service_name_on_proposal, pricing_type,
       price_amount, scope_of_work, fee_raw
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku IN ('TA01', 'TA05', 'CSS030')
ORDER BY sku;
```

若 `IN (...)` 返回行数少于列表长度，说明有 SKU 不存在或 inactive——**不要** patch 不存在的 SKU。

### 5）BVI — 列出 package 及所含 SKU

```sql
SELECT p.package_id, p.package_name, p.package_semantic_for_ai,
       array_agg(ps.sku ORDER BY ps.sku) AS skus
FROM mdm_packages p
JOIN mdm_package_services ps
  ON ps.package_id = p.package_id AND ps.category_id = p.category_id
WHERE p.category_id = 'harneys-bvi'
  AND p.status = 'ACTIVE'
GROUP BY p.package_id, p.package_name, p.package_semantic_for_ai;
```

## 反例（会导致 query 失败）

```sql
-- BAD: 臆造列 price_note
SELECT sku, price_amount, price_note FROM mdm_services WHERE ...

-- BAD: 空参数调用 query_data
{}

-- BAD: JOIN 缺少 category_id 对齐（可能错行）
JOIN mdm_services s ON s.sku = ps.sku

-- BAD: 未 filter status
WHERE category_id = 'au-services'
```

## 表

| 表 | 用途 |
|----|------|
| `mdm_services` | SKU、定价、`service_group` / `department_team` |
| `mdm_packages` | 命名方案包 |
| `mdm_package_services` | Package ↔ SKU |

更多 region 片段：`proposal-composer` → `references/bvi-sql.md` / `au-sql.md`。

**`query_data` 调用格式**（空参数禁止等）→ Postgres MCP tool description，此处不重复。
