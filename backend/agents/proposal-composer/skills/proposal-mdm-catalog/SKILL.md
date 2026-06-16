---
name: proposal-mdm-catalog
description: >-
  MDM catalog SQL patterns for proposal-composer when BD/sales intent is clear on region
  but package/SKU still needs lookup, comparison, or keyword search. Read-only Postgres;
  load after proposal-composer when exploration beats guessing.
---

# Proposal MDM Catalog — Skill（对内）

**何时加载**：销售说的方案还不对应具体 `package_id` / SKU，或需要 **对比多个 package、按关键词搜服务、看 package 里含哪些 SKU** 时。若用户已明确 package 名且你认得 ID，直接 patch，不必为查而查。

## 原则

- 只读 SELECT；`category_id` + `status = 'ACTIVE'`。
- 查完用 **销售语言** 总结；确认后再 `patch_proposal_state`——**选型不能只留在对话里**。
- 价格展示以 patch 后算价为准；SQL 里的 `price_amount` 仅作推荐参考。

## 表

| 表 | 用途 |
|----|------|
| `mdm_services` | SKU、定价、`service_group` / `department_team` |
| `mdm_packages` | 命名方案包 |
| `mdm_package_services` | Package ↔ SKU |

## 常见查法

**列出某 region 所有 package（BVI 示例）**

```sql
SELECT p.package_id, p.package_name, p.package_semantic_for_ai,
       array_agg(ps.sku ORDER BY ps.sku) AS skus
FROM mdm_packages p
JOIN mdm_package_services ps ON ps.package_id = p.package_id AND ps.category_id = p.category_id
WHERE p.category_id = 'harneys-bvi' AND p.status = 'ACTIVE'
GROUP BY p.package_id, p.package_name, p.package_semantic_for_ai;
```

**按销售口述关键词搜 SKU**

```sql
SELECT sku, service_group, service_name_on_proposal, pricing_type, price_amount, price_spec
FROM mdm_services
WHERE category_id = 'harneys-bvi'
  AND status = 'ACTIVE'
  AND (
    service_name_on_proposal ILIKE '%incorp%'
    OR sku_semantic_for_ai ILIKE '%incorp%'
  )
ORDER BY service_group, sku;
```

**AU advisory（排除 audit ADT 前缀时）**

```sql
SELECT sku, department_team, service_name_on_proposal, pricing_type, price_amount, scope_of_work
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku NOT LIKE 'ADT%'
ORDER BY department_team, sku
LIMIT 50;
```

更多 BVI/AU 片段见 Skill `proposal-composer` → `references/bvi-sql.md` / `au-sql.md`。
