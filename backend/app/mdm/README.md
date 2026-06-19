# MDM Catalog（PostgreSQL 模拟）

> **产品目录**在 `mdm_services` / `mdm_packages`。  
> **Category 路由**在 `agents/proposal-composer/knowledge/categories.yaml`。

## 表

| 表 | 说明 |
|----|------|
| `mdm_services` | SKU / 定价 / `price_spec` |
| `mdm_packages` | Solution Package（AU：`package_name` = `内部名*外部名`） |
| `mdm_package_services` | package ↔ SKU |

## 初始化

```bash
cd backend
alembic upgrade head          # includes 008_seed_bvi_mdm_catalog
pip install -e ".[mdm]"
python scripts/seed_bvi_catalog.py   # re-seed BVI only from JSON snapshot
python scripts/export_bvi_catalog_json.py  # regenerate JSON from bundled xlsx
python scripts/seed_mdm_catalog.py   # full re-seed (BVI + AU workbooks)
```

Bundled BVI source workbook: `app/mdm/data/bvi-products-pricing-mock0618.xlsx`  
Migration snapshot: `app/mdm/data/bvi_catalog.json`

## Agent 如何读

| 需求 | 来源 |
|------|------|
| 列 category、默认 template | `knowledge/categories.yaml` |
| 搜 SKU、列 package | `mdm_*` 产品表（MCP postgres） |
| 模版章节、placeholder | `templates/{id}/template.yaml` |
