---
name: proposal-mdm-catalog
description: >-
  Read-only Postgres MDM catalog queries for Proposal Composer: schema-first
  SELECT on mdm_services, mdm_packages, and mdm_package_services. Use when
  package_id or SKU is unknown, when listing packages in scope, comparing
  packages, keyword-searching services, or loading all SKUs for a package—not
  when patching an existing draft or editing client facts.
---

# Proposal MDM Catalog — SQL Skill

## 与 System Prompt 的分工

| 层 | 内容 |
|----|------|
| **System prompt** | 角色、catalog 只读、tool 并行/顺序 |
| **Postgres MCP tools** | `get_schema` / `describe_table` / `query_data` 参数 |
| **本 Skill** | MDM 表关系、列名、SQL 模板、jurisdiction filter |

触发后 catalog 查数以本 Skill 为准；**回复正文遵守 system prompt 对外铁律**。

## Catalog 查询原则

1. **Catalog 回答「能卖什么、标价多少」；draft 回答「这份 proposal 里有什么」** — 已写入 draft 的改单、调价、改 SOW 不再查 catalog。
2. **Schema 先于 SQL** — 列名以 `get_schema` / `describe_table` 为准，禁止臆造字段。
3. **Scope 与 template 一致** — 过滤 `catalog_filter`（jurisdiction + bu）+ `status = 'ACTIVE'`。
4. **查是为了 materialize** — 返回 **完整 row**（含 `description`、`department_team`、定价字段）交给 add tools；勿截断字段、勿 `run_skill_script`。
5. **SQL 是手段，销售确认是闸门** — 查完用销售语言总结；选型确认后再写入 draft。

## 表与 JOIN

| 表 | 用途 |
|----|------|
| `mdm_services` | SKU、定价、展示字段 |
| `mdm_packages` | 方案包 |
| `mdm_package_services` | Package ↔ SKU |

Package 内容查询必须 JOIN `mdm_packages` 限定 `jurisdiction` / `bu`，且 `ps.sku = s.sku` 并匹配 `s.jurisdiction` / `s.bu`。

## Schema-first

**禁止**臆造列名（`price_note` **不存在**）。

1. `postgres_get_schema` 一次，或并行 `describe_table` 三张 MDM 表。
2. 只 SELECT 已确认存在的列。
3. `postgres_query_data` — 非空 SELECT；`status = 'ACTIVE'` + template `catalog_filter`（`jurisdiction`, `bu`）。
4. 无依赖的多条 SELECT 可同一轮并行。

### `mdm_services` 常用列

| 列 | 用途 |
|----|------|
| `sku`, `jurisdiction`, `bu`, `status` | 过滤 |
| `service_name`, `description`, `scope_of_work`, `sku_semantic_for_ai` | 展示 / 搜索 |
| `department_team` | BVI department 分组（add 时必须传入） |
| `pricing_type`, `price_amount`, `price_currency` | 定价 |
| `fee_raw`, `footnotes` | 非 FIXED 展示 |
| `billing_frequency`, `recurring` | 周期 |

### `pricing_type` → materializer

| 类型 | 传给 add tool | 说明 |
|------|---------------|------|
| `FIXED` | `price_amount` → draft `price.amount` | fee table 显示 amount |
| `UNIT_RATE` / `RANGE` / `BASE_PLUS*` / `MATRIX_REF` | `price_amount` + `fee_raw` | 需数量/事实时先问销售再定 total |

BVI `fee_layout` 通常用 **description** 列 — SELECT 与 add 时勿丢 `description`、`department_team`。

## SQL 模板

占位：`JURISDICTION` / `BU` ← template `catalog_filter`；`PACKAGE_ID` / `KEYWORD` / `SKU_*` ← 实际值。

### 列 packages

```sql
SELECT package_id, package_name, package_semantic_for_ai
FROM mdm_packages
WHERE jurisdiction = 'JURISDICTION'
  AND bu = 'BU'
  AND status = 'ACTIVE'
ORDER BY package_name;
```

### Package 含哪些 services

```sql
SELECT ps.package_id, ps.sku,
       s.service_name, s.description, s.department_team,
       s.pricing_type, s.price_currency, s.price_amount,
       s.billing_frequency, s.recurring, s.scope_of_work,
       s.fee_raw, s.footnotes
FROM mdm_package_services ps
JOIN mdm_packages p ON p.package_id = ps.package_id
JOIN mdm_services s
  ON ps.sku = s.sku AND s.jurisdiction = p.jurisdiction AND s.bu = p.bu
WHERE p.jurisdiction = 'JURISDICTION'
  AND p.bu = 'BU'
  AND ps.package_id = 'PACKAGE_ID'
  AND p.status = 'ACTIVE'
  AND s.status = 'ACTIVE'
ORDER BY ps.sku;
```

### 关键词搜 SKU

```sql
SELECT sku, department_team, service_name, description,
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

### 多 SKU 核对

```sql
SELECT sku, department_team, service_name, description,
       pricing_type, price_currency, price_amount,
       billing_frequency, recurring, scope_of_work, fee_raw, footnotes
FROM mdm_services
WHERE jurisdiction = 'JURISDICTION'
  AND bu = 'BU'
  AND status = 'ACTIVE'
  AND sku IN ('SKU_1', 'SKU_2')
ORDER BY sku;
```

返回行数少于 SKU 列表 → 存在 inactive/无效 SKU，勿 materialize。

### Package 聚合 SKU

```sql
SELECT p.package_id, p.package_name, p.package_semantic_for_ai,
       array_agg(ps.sku ORDER BY ps.sku) AS skus
FROM mdm_packages p
JOIN mdm_package_services ps ON ps.package_id = p.package_id
WHERE p.jurisdiction = 'JURISDICTION'
  AND p.bu = 'BU'
  AND p.status = 'ACTIVE'
GROUP BY p.package_id, p.package_name, p.package_semantic_for_ai;
```

### Harneys BVI — PKG003 示例

```sql
SELECT ps.package_id, ps.sku,
       s.service_name, s.description, s.department_team,
       s.pricing_type, s.price_currency, s.price_amount,
       s.billing_frequency, s.recurring, s.fee_raw, s.footnotes
FROM mdm_package_services ps
JOIN mdm_packages p ON p.package_id = ps.package_id
JOIN mdm_services s
  ON ps.sku = s.sku AND s.jurisdiction = p.jurisdiction AND s.bu = p.bu
WHERE p.jurisdiction = 'BVI'
  AND p.bu = 'Harneys'
  AND ps.package_id = 'PKG003'
  AND p.status = 'ACTIVE'
  AND s.status = 'ACTIVE'
ORDER BY s.department_team NULLS LAST, ps.sku;
```

## Jurisdiction filter

| Template | `jurisdiction` | `bu` |
|----------|----------------|------|
| `harneys-bvi` | `BVI` | `Harneys` |
| `au-advisory` | `AU` | `Incorp AU` |

AU advisory 勿主动加 audit-only SKU（如 `ADT%`）。BVI `department_team` 为 `nan` 时在 SQL 用 `CASE` 或后续 patch draft row。

## 反例

```sql
-- 臆造列
SELECT sku, price_note FROM mdm_services ...

-- JOIN 未限定 package jurisdiction/bu
JOIN mdm_services s ON s.sku = ps.sku

-- 缺 status 过滤
WHERE jurisdiction = 'AU'

-- 空 query_data {}
```

**反例**：只 SELECT `sku, price_amount` → BVI preview Service 列只剩 SKU 代码。
