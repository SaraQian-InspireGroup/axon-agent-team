# BVI catalog SQL

Category: `harneys-bvi`

## Packages

```sql
SELECT package_id, package_name, package_semantic_for_ai
FROM mdm_packages
WHERE category_id = 'harneys-bvi' AND status = 'ACTIVE';
```

## Services by group

```sql
SELECT service_group, sku, service_name_on_proposal, pricing_type, price_amount, price_spec
FROM mdm_services
WHERE category_id = 'harneys-bvi' AND status = 'ACTIVE'
ORDER BY service_group, sku;
```

## Package contents

```sql
SELECT ps.package_id, ps.sku, s.service_name_on_proposal, s.pricing_type
FROM mdm_package_services ps
JOIN mdm_services s ON s.sku = ps.sku AND s.category_id = ps.category_id
WHERE ps.category_id = 'harneys-bvi' AND ps.package_id = 'PKG-BVI-INCORP-STD';
```

## Pricing facts

Ask for `share_count` when selected SKUs include TIERED government fees (`price_spec.dimension = 'share_count'`). Surface this to the user in sales language (e.g. share capital / number of shares), not as a field name.
