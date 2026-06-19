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
3. **`postgres_query_data`**（`query` 参数必填、非空 SELECT）；scope 带 template 的 **`catalog_filter`**（如 `jurisdiction`/`bu`）+ **`status = 'ACTIVE'`**。
4. 用销售语言总结；**确认后再** 把查询返回的 package/service 行作为原始 JSON object/array 传给 `add_package_to_proposal_draft` / `add_services_to_proposal_draft` 写入 draft fee section。不要把 row 再包成字符串。

`mdm_services` 常用列（以 describe 结果为准）：

| 列 | 用途 |
|----|------|
| `sku`, `jurisdiction`, `bu`, `status` | 过滤 |
| `service_name`, `scope_of_work`, `sku_semantic_for_ai` | 展示 / 搜索 |
| `department_team` | 部门 / 团队 |
| `pricing_type`, `price_amount`, `price_currency` | 定价类型与汇总金额 |
| `fee_raw`, `footnotes` | 非 FIXED 类型的 client-facing 价格说明 |
| `billing_frequency`, `recurring` | 周期 |

**不存在**：`price_note`、`price_notes` 等——勿使用。

## `pricing_type` 与 `price_amount` / `fee_raw`

平台 materialize 后：

| `pricing_type` | 汇总 / payment total 用 | AU frequency 表：对应 billing 列 | AU frequency 表：Total 列 |
|----------------|-------------------------|----------------------------------|-------------------------|
| `FIXED` | `price_amount` → draft `price.amount` | 格式化 `price.amount` | 年化 total（Monthly×12 / Quarterly×4 / 其余×1） |
| `UNIT_RATE` / `RANGE` / `BASE_PLUS` / `BASE_PLUS_VARIABLE` / `MATRIX_REF` | `price_amount` → draft `price.amount` | `fee_raw` | 同上，用 `price.amount` 年化 |

Agent 职责：

- 把 MCP 查到的 **完整 service row**（含 `pricing_type`、`price_amount`、`fee_raw`）传给 add tools；不要丢字段。
- `UNIT_RATE` / `MATRIX_REF` 等需乘数量或确认事实时：先问销售，再把 **算好的 total** patch 到 `price.amount`；**不要**改 `fee_raw` 里的单价/规则说明。
- `RANGE` 且 `price_amount` 为空：fee table 仍展示 `fee_raw`；汇总缺金额时向销售确认后再 patch `price.amount`。
- 销售 override 总价：patch `price.amount`；必要时把 `edit_state.price` 设为 `manual`。

## 原则

- 只读 SELECT；用当前 template 的 `catalog_filter`（通常是 `jurisdiction` + `bu`）+ `status = 'ACTIVE'`。
- Package ↔ SKU 的 JOIN 必须带 `ps.sku = s.sku`；package scope 由 `mdm_packages.jurisdiction/bu` 过滤。
- SQL 里的 `price_amount` 仅作推荐；对外报价以 draft fee rows 为准。
- 会修改 draft 的 tools 必须顺序调用；多个 service 一次性放进 `services` array，不要并发调用多次。

## 通用 Few-shot 工作流

### 1）首次查 catalog（推荐顺序）

```
→ postgres_describe_table("mdm_services")
→ postgres_query_data: 按当前 template catalog_filter 列出 package
→ postgres_query_data: 按关键词或 package_id 查 SKU
→ 向用户确认 package/SKU
→ add_package_to_proposal_draft({
    "package": {"package_id": "PKG-AU-EXAMPLE", "package_name": "Example Package"},
    "services": [{"sku": "TA01", "service_name": "...", "pricing_type": "FIXED", "price_amount": 600, "fee_raw": "600"}]
  })
  或 add_services_to_proposal_draft({
    "services": [{"sku": "GI01", "service_name": "...", "pricing_type": "UNIT_RATE", "price_amount": 4500, "fee_raw": "4500 per round of R&D Financing"}]
  })
```

### 2）列出当前 scope 的 packages

写 SQL 时用当前 template 的 `catalog_filter` 替换示例中的 `'JURISDICTION'` / `'BU'`；用实际 package id / SKU / keyword 替换其他占位值。

```sql
SELECT package_id, package_name, package_semantic_for_ai
FROM mdm_packages
WHERE jurisdiction = 'JURISDICTION'
  AND bu = 'BU'
  AND status = 'ACTIVE'
ORDER BY package_name;
```

### 3）已知 package_id，查包含哪些服务

```sql
SELECT ps.package_id, ps.sku,
       s.service_name, s.pricing_type,
       s.price_currency, s.price_amount,
       s.billing_frequency, s.recurring, s.scope_of_work,
       s.fee_raw, s.footnotes
FROM mdm_package_services ps
JOIN mdm_packages p
  ON p.package_id = ps.package_id
JOIN mdm_services s
  ON ps.sku = s.sku AND s.jurisdiction = p.jurisdiction AND s.bu = p.bu
WHERE p.jurisdiction = 'JURISDICTION'
  AND p.bu = 'BU'
  AND ps.package_id = 'PACKAGE_ID'
  AND p.status = 'ACTIVE'
  AND s.status = 'ACTIVE'
ORDER BY ps.sku;
```

### 4）销售口述「incorporation / tax / payroll」— 关键词搜 SKU

```sql
SELECT sku, department_team, service_name,
       pricing_type, price_currency, price_amount,
       billing_frequency, recurring, scope_of_work, fee_raw, footnotes
FROM mdm_services
WHERE jurisdiction = 'JURISDICTION'
  AND bu = 'BU'
  AND status = 'ACTIVE'
  AND (
    service_name ILIKE '%KEYWORD%'
    OR sku_semantic_for_ai ILIKE '%KEYWORD%'
  )
ORDER BY department_team, sku;
```

### 5）用户给了多个 SKU 代码 — 批量核对（SKU 必须来自 catalog，勿编造）

```sql
SELECT sku, service_name, pricing_type,
       price_currency, price_amount,
       billing_frequency, recurring, scope_of_work, fee_raw, footnotes
FROM mdm_services
WHERE jurisdiction = 'JURISDICTION'
  AND bu = 'BU'
  AND status = 'ACTIVE'
  AND sku IN ('SKU_1', 'SKU_2')
ORDER BY sku;
```

若 `IN (...)` 返回行数少于列表长度，说明有 SKU 不存在或 inactive——**不要** patch 不存在的 SKU。

### 6）按 package 聚合 SKU

```sql
SELECT p.package_id, p.package_name, p.package_semantic_for_ai,
       array_agg(ps.sku ORDER BY ps.sku) AS skus
FROM mdm_packages p
JOIN mdm_package_services ps
  ON ps.package_id = p.package_id
WHERE p.jurisdiction = 'JURISDICTION'
  AND p.bu = 'BU'
  AND p.status = 'ACTIVE'
GROUP BY p.package_id, p.package_name, p.package_semantic_for_ai;
```

## Jurisdiction notes

- AU Advisory 当前 template filter 是 `jurisdiction = 'AU'`, `bu = 'Incorp AU'`；AU `package_name` 可能是 `内部名*外部名`。若只做 advisory，不要主动加入 audit-only SKU（如 `ADT%`）。
- Harneys BVI 当前 template filter 是 `jurisdiction = 'BVI'`, `bu = 'Harneys'`；若 catalog 价格需要股数/股本口径才能确定，用销售语言确认后再写入 draft inputs 或手动调整 fee row。

## 反例（会导致 query 失败）

```sql
-- BAD: 臆造列 price_note
SELECT sku, price_amount, price_note FROM mdm_services WHERE ...

-- BAD: 空参数调用 query_data
{}

-- BAD: package contents 查询未通过 mdm_packages 限定 jurisdiction/bu
JOIN mdm_services s ON s.sku = ps.sku

-- BAD: 未 filter status
WHERE jurisdiction = 'AU'
```

## 表

| 表 | 用途 |
|----|------|
| `mdm_services` | SKU、定价、`service_name` / `department_team` |
| `mdm_packages` | 命名方案包 |
| `mdm_package_services` | Package ↔ SKU |

**`query_data` 调用格式**（空参数禁止等）→ Postgres MCP tool description，此处不重复。
