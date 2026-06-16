# MDM Catalog（PostgreSQL 模拟）

> **产品目录**在 `mdm_services` / `mdm_packages`。  
> **Category 路由**在 `agents/proposal-composer/knowledge/categories.yaml`。

## 表

| 表 | 说明 |
|----|------|
| `mdm_services` | SKU / 定价 / `price_spec` |
| `mdm_packages` | Solution Package |
| `mdm_package_services` | package ↔ SKU |
| `mdm_package_name_aliases` | AU legacy 名称 |

## 初始化

```bash
cd backend
alembic upgrade head
pip install -e ".[mdm]"
python scripts/seed_mdm_catalog.py
```

## Agent 如何读

| 需求 | 来源 |
|------|------|
| 列 category、默认 template | `knowledge/categories.yaml` |
| 搜 SKU、列 package | `mdm_*` 产品表（MCP postgres） |
| 模版章节、placeholder | `templates/{id}/template.yaml` |
