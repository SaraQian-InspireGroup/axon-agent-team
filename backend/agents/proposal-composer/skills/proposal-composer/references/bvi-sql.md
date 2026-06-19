# BVI catalog SQL

Category: `harneys-bvi`

## Schema-first（必做）

写 MDM SQL **之前**先 `postgres_describe_table("mdm_services")`（及需要的 package 表）。  
只 SELECT describe 里存在的列；**无** `price_note`——用 `fee_raw`、`footnotes`、`price_spec`。

## Few-shot 1 — Packages

```sql
SELECT package_id, package_name, package_semantic_for_ai
FROM mdm_packages
WHERE category_id = 'harneys-bvi' AND status = 'ACTIVE';
```

## Few-shot 2 — Services by group

```sql
SELECT service_group, sku, service_name_on_proposal, pricing_type,
       price_amount, price_spec
FROM mdm_services
WHERE category_id = 'harneys-bvi' AND status = 'ACTIVE'
ORDER BY service_group, sku;
```

## Few-shot 3 — Package contents

```sql
SELECT ps.package_id, ps.sku, s.service_name_on_proposal, s.pricing_type,
       s.price_amount, s.fee_raw
FROM mdm_package_services ps
JOIN mdm_services s
  ON s.sku = ps.sku AND s.category_id = ps.category_id
WHERE ps.category_id = 'harneys-bvi'
  AND ps.package_id = 'PKG-BVI-INCORP-STD'
  AND s.status = 'ACTIVE';
```

## Few-shot 4 — TIERED 政府费（需业务输入）

若 `pricing_type = 'TIERED'` 且 `price_spec` 含 `share_count`，向用户确认股数/股本口径。把该事实写入 draft facts/inputs 中与模板约定的字段；不要在聊天里使用裸字段名。

```sql
SELECT sku, service_name_on_proposal, pricing_type, price_amount, price_spec
FROM mdm_services
WHERE category_id = 'harneys-bvi'
  AND status = 'ACTIVE'
  AND pricing_type = 'TIERED';
```

## Pricing facts

Ask for share count in sales language (e.g. share capital / number of shares), not as a raw field name.
