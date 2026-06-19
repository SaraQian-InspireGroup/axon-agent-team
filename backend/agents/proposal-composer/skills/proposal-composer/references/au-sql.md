# AU catalog SQL

Category: `au-services`  
Templates: `au-advisory` (default), future `au-audit` (ADT% SKUs)

## Schema-first（必做）

写任何 MDM SQL **之前**：

1. `postgres_describe_table("mdm_services")`（必要时同样 describe `mdm_packages`, `mdm_package_services`）
2. 只使用 describe 返回的列名
3. 再 `postgres_query_data` 执行 SELECT

**不存在** `price_note` 列。费用说明用 `fee_raw`、`footnotes`、`price_spec`。

## Few-shot 1 — 列出 AU packages

```sql
SELECT package_id, package_name, package_semantic_for_ai
FROM mdm_packages
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
ORDER BY package_name;
```

## Few-shot 2 — Advisory SKU 浏览（排除 audit ADT 前缀）

```sql
SELECT sku, department_team, service_name_on_proposal, pricing_type,
       price_amount, scope_of_work
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku NOT LIKE 'ADT%'
ORDER BY department_team, sku;
```

## Few-shot 3 — 某 package 下有哪些 SKU

```sql
SELECT ps.package_id, ps.sku,
       s.service_name_on_proposal, s.pricing_type, s.price_amount,
       s.scope_of_work, s.fee_raw
FROM mdm_package_services ps
JOIN mdm_services s
  ON ps.sku = s.sku AND ps.category_id = s.category_id
WHERE ps.category_id = 'au-services'
  AND ps.package_id = 'PKG-AU-REPLACE-ME'
  AND s.status = 'ACTIVE'
ORDER BY ps.sku;
```

## Few-shot 4 — 按 SKU 列表核对（仅 patch 返回存在的 SKU）

```sql
SELECT sku, service_name_on_proposal, pricing_type,
       price_amount, billing_frequency, scope_of_work
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku IN ('TA01', 'TA05', 'CSS030')
ORDER BY sku;
```

## Few-shot 5 — 关键词搜服务

```sql
SELECT sku, department_team, service_name_on_proposal,
       pricing_type, price_amount, price_spec
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku NOT LIKE 'ADT%'
  AND (
    service_name_on_proposal ILIKE '%xero%'
    OR sku_semantic_for_ai ILIKE '%xero%'
  )
ORDER BY department_team, sku;
```

## Optional sections

Enable optional draft sections with `enable_proposal_draft_section`, for example:

```text
enable_proposal_draft_section("credentials", true)
enable_proposal_draft_section("appendix", true)
```

Then fill `appendix` or peripheral picks as needed.
