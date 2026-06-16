# AU advisory catalog SQL

Category: `au-services`  
Template: `au-advisory`

## Advisory SKUs (non-audit)

```sql
SELECT sku, department_team, service_name_on_proposal, pricing_type,
       price_amount, scope_of_work
FROM mdm_services
WHERE category_id = 'au-services'
  AND status = 'ACTIVE'
  AND sku NOT LIKE 'ADT%'
ORDER BY department_team, sku;
```

## Optional sections

Enable via patch:

```json
{ "op": "enable_sections", "section_ids": ["credentials", "appendix"] }
```

Then fill `appendix` or peripheral picks as needed.
