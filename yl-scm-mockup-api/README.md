# yl-scm-mockup-api

独立 Flask API，为 `yl-scm-mockup` 计划中心 Tab1/Tab2 与履约中心提供 JSON 接口。

## 本地启动

```bash
cd yl-scm-mockup-api
cp .env.example .env   # 配置 YL_DATABASE_URL
uv sync
uv run flask --app wsgi:app run --port 5001
```

前端 `.env`：

```
VITE_MOCKUP_API_BASE_URL=http://localhost:5001/api/v1
```

## Tab1 数据逻辑

- 基地库存：`yl_base_warehouse_inventory_report` + `yl_spot_inventory`（待检/合格/不可发）
- 在途/可发：`yl_forward_transfer` 按基地×品项 SUM/MAX
- 区域列：`yl_forward_transfer` pivot + `yl_sales_warehouse_inventory_report.issued_not_dispatched`

详见 `docs/architecture-and-api.md`。
