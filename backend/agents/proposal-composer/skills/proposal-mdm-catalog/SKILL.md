---
name: proposal-mdm-catalog
description: >-
  Read-only MDM SQL templates when region/BU is known but package_id or SKU still needs keyword
  search, comparison, or package composition lookup. Load for catalog exploration—not for
  post-selection edits (use patch_proposal_state per its tool description).
---

# Proposal MDM Catalog — Skill（对内）

**何时加载**：销售说的方案还不对应具体 `package_id` / SKU，或需要 **对比 package、按关键词搜服务、看 package 含哪些 SKU**。

**何时不必加载**：用户已明确 package/SKU 且你要做的是 **改单、增删服务、改客户**——直接 patch（tool description）；不要为改单反复 SQL。

## 原则

- 只读 SELECT；`category_id` + `status = 'ACTIVE'`。
- 查完用 **销售语言** 总结；**确认后再写入 selection**（选型不能只留在对话里）。
- SQL 里的 `price_amount` 仅作推荐；对外报价以 patch 后 **line_items** 为准。

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

更多片段：Skill `proposal-composer` → `references/bvi-sql.md` / `au-sql.md`。

**`query_data` 调用格式**（空参数禁止等）→ Postgres MCP tool description，此处不重复。
