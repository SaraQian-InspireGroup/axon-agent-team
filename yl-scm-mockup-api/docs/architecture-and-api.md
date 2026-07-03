# YL SCM Mockup API — 架构与 API 设计

独立 Python 后端，为 `yl-scm-mockup` 前端提供计划中心（2 Tab）、履约中心（1 Tab）的数据与筛选能力，并提供履约补录单创建接口（供未来 Agent 调用）。

与以下项目 **零代码依赖**，可单独仓库、单独部署：

| 项目 | 职责 |
|------|------|
| `backend/`（agent platform） | Nova / yl-worker1 对话、Memory、MCP 查数 |
| `frontend/` | 主平台 Chat |
| `yl-scm-mockup/` | 本 API 的唯一 UI 消费者 |
| **`yl-scm-mockup-api/`（本文）** | 业务表格 JSON API |

---

## 1. 目标与非目标

### 目标

- 为 3 张业务表提供 **列表 + Filter 查询**（query 参数驱动，对齐前端 `FilterPanel` 字段）。
- 为履约中心提供 **创建补录单** `POST`（Agent / 前端均可调用）。
- 响应 JSON **形状对齐** `yl-scm-mockup/src/data/mockData.ts`，前端改动最小。
- 支持本地开发与 **Vercel 独立部署**。

### 非目标（首期）

- 分货导入/导出、分货下发、单元格 inline 保存（Tab1 分配量编辑持久化）。
- 补录单拆行/作废/加量/生成调拨单等业务工作流（仅预留 PATCH 扩展点）。
- 用户登录体系（可选 API Key 保护写接口即可）。

---

## 2. 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 运行时 | Python 3.12+ | 与 monorepo 其他 Python 版本接近 |
| Web | **Flask 3** + `flask-cors` | 简单 WSGI；Vercel 通过 `vercel.json` 挂载 |
| DB 驱动 | `psycopg[binary]` 或 SQLAlchemy 2（Core） | 避免 ORM 过重；只读/读写分连接 |
| 配置 | `pydantic-settings` + `.env` | 本地 / Vercel Environment Variables |
| 校验 | Pydantic v2 | Request/Response schema |
| 包管理 | `uv` + `pyproject.toml` | 与 platform backend 习惯一致 |

### Vercel 约束

- **无持久本地磁盘**：写库必须用云 Postgres（Neon / Supabase / Vercel Postgres），不能用 SQLite 生产写。
- **Serverless 冷启动**：DB 用短连接或 Neon serverless driver；连接池交给 Neon pooler。
- 入口：`api/index.py` 导出 `app` 或 `vercel.json` → `yl-scm-mockup-api/wsgi.py:app`。

---

## 3. 数据架构（双库）

```
┌─────────────────────┐
│  yl-scm-mockup      │
│  (React / Vite)     │
└──────────┬──────────┘
           │ HTTPS  /api/v1/*
           ▼
┌─────────────────────┐
│  yl-scm-mockup-api  │
│  (Flask)            │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌──────────┐  ┌──────────────────┐
│ YL DB    │  │ Mockup DB        │
│ (只读)   │  │ (读写)           │
└──────────┘  └──────────────────┘
```

### 3.1 YL Database（只读）— `YL_DATABASE_URL`

来源：`backend/migrations/sql/023_yl_milk_powder_mockup.sql` 及种子脚本。

**计划中心 Tab1 / Tab2** 主要读：

| 表 | 用途 |
|----|------|
| `yl_base_warehouse_inventory_report` | 基地仓：待检、合格、在途（合并） |
| `yl_forward_transfer` | 基地→销仓分货；区域 6 指标、`from_available`、在途拆分 |
| `yl_sales_warehouse_inventory_report` | 销仓：`issued_not_dispatched`、单仓指标；Tab2 分城 pivot |
| `yl_product` / `yl_warehouse` | Filter 下拉、系列、仓名 |
| `yl_national_sales_warehouse_inventory_report` | Tab2 合计行辅助（可选） |

事业部 filter 对齐 mockup：`成人营养品事业部` / `CRYYBU`（执行 `yl_business_unit_adult_nutrition.sql` 后）。

**字段映射要点**（详见前期数据对齐分析）：

- 基地 **待检/合格**：`from_store_num_d` / `from_store_num_h`。
- 基地 **可发量**：`yl_forward_transfer.from_available`（非基地报表列）。
- 基地 **正常/中转在途**：`from_store_transit` / `from_store_transit_zt`（zt 常为空）。
- 基地 **待检不可发 / 合格不可发**：schema 无直列 → 首期返回 `0` 或 Phase B 从 `yl_spot_inventory` 聚合。
- 区域 **6 指标**：以 `yl_forward_transfer` 为主；**已下发未发货** join `yl_sales_warehouse_inventory_report.issued_not_dispatched`。
- `%` / `21.5天` 等字符串：API 层 parse 为 number；缺失时用 schema 注释公式补算。

### 3.2 Mockup Database（读写）— `MOCKUP_DATABASE_URL`

履约中心 **分仓补录单** 在 YL schema 中 **不存在**，必须自建表。

建议表名：`mock_branch_replenishment_order`（前缀 `mock_` 与 YL 表区分）。

首期字段对齐 `BranchReplenishmentOrder`（`mockData.ts`）。写操作仅落此库。

**Phase A 备选**：若 YL 未就绪，计划 Tab 也可暂时 seed 进 Mockup DB（与 `mockData.ts` 一致），YL 只读作为 Phase B 切换开关（`DATA_SOURCE=yl|seed`）。

---

## 4. 项目目录结构（建议）

```
yl-scm-mockup-api/
├── api/
│   └── index.py              # Vercel serverless 入口（re-export app）
├── app/
│   ├── __init__.py           # create_app()
│   ├── config.py             # Settings
│   ├── extensions.py         # CORS 等
│   ├── db/
│   │   ├── yl.py             # 只读 YL 连接
│   │   └── mockup.py         # 读写 Mockup 连接
│   ├── routes/
│   │   ├── health.py
│   │   ├── meta.py           # filter 元数据
│   │   ├── plan_transfer.py
│   │   ├── plan_inventory.py
│   │   └── fulfillment.py
│   ├── services/
│   │   ├── transfer_allocation.py
│   │   ├── national_inventory.py
│   │   └── branch_replenishment.py
│   ├── repositories/         # SQL 查询（可选）
│   └── schemas/              # Pydantic models
├── migrations/
│   └── 001_mock_branch_replenishment.sql
├── docs/
│   └── architecture-and-api.md   # 本文
├── tests/
├── .env.example
├── pyproject.toml
├── wsgi.py                   # 本地 gunicorn/flask run
└── vercel.json
```

### 分层约定

- **routes**：HTTP、参数解析、状态码。
- **services**：业务组装、pivot、filter 逻辑、YL↔DTO 映射。
- **repositories**：纯 SQL（便于单测 mock）。
- **schemas**：与前端 TypeScript 类型一一对应。

---

## 5. API 通用约定

### 5.1 Base URL

```
/api/v1
```

前端环境变量：`VITE_MOCKUP_API_BASE_URL`（与 Nova 的 `VITE_API_BASE_URL` **分开**；Nova 仍指向 platform `:8000`）。

### 5.2 响应包络

**列表接口**（推荐）：

```json
{
  "items": [ ... ],
  "total": 42,
  "updated_at": "2026-07-02T08:17:00+08:00",
  "filters_applied": { "business_unit": "成人营养品事业部" }
}
```

**单条 / 创建**：

```json
{
  "item": { ... }
}
```

**错误**：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "inbound_logic_warehouse is required"
  }
}
```

HTTP 状态：`400` 参数错误，`404` 无数据，`500` 内部错误。

### 5.3 Filter 查询参数

- 全部 **可选**；空字符串视为未传。
- 多值未来可用重复 key 或逗号分隔；首期均为单选，与当前 `FilterPanel` 一致。
- 日期格式：`YYYY-MM-DD`。
- 分页（可选，首期可不分页）：`page`（默认 1）、`page_size`（默认 100，最大 500）。

### 5.4 CORS

允许来源：`MOCKUP_CORS_ORIGINS`（逗号分隔，如 `http://localhost:5174`）。

### 5.5 Agent 写接口鉴权（可选）

`POST /fulfillment/branch-replenishment` 支持：

```
Authorization: Bearer <MOCKUP_API_KEY>
```

未配置 `MOCKUP_API_KEY` 时开发环境可跳过。

---

## 6. API 端点详设

### 6.1 Health

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | `{ "status": "ok", "yl_db": "ok\|skip\|error", "mockup_db": "ok\|error" }` |

---

### 6.2 元数据 — Filter 下拉

前端打开 Filter 时可预加载；也可由各列表接口内嵌 `filter_options`（二选一，推荐独立 meta 接口缓存）。

#### `GET /api/v1/meta/filters/plan`

**Response `filter_options`：**

```json
{
  "business_units": ["成人营养品事业部"],
  "product_series": ["中老年", "奶片奶贝"],
  "base_warehouses": ["武汉基地", "呼市基地", "天津基地", "合肥基地"],
  "sales_warehouses": ["武汉", "合肥", "南京", "天津", "郑州", "广州"],
  "products": [
    { "code": "MOCK_YLP001", "name": "伊利欣活…" }
  ]
}
```

来源：`yl_product`、`yl_warehouse`（`site_type` 区分基地/销售）、distinct `pro_series`；名称映射层去掉「基地仓」「销售仓」后缀以贴近 UI。

#### `GET /api/v1/meta/filters/fulfillment`

```json
{
  "logic_warehouses": ["天津销售仓一盘货仓", "…"],
  "initial_ship_warehouses": ["天津基地仓一盘货仓", "…"],
  "statuses": ["全部", "生效", "作废"],
  "transfer_gen_statuses": ["全部", "未生成", "已生成"],
  "business_units": ["成人营养品事业部"],
  "products": [ { "code": "…", "name": "…" } ]
}
```

逻辑仓枚举首期可 **配置表/常量**（YL 无「一盘货仓」命名）；与 `FULFILL_FILTER_OPTIONS` 对齐。

---

### 6.3 计划中心 Tab1 — 正向分货销售仓调拨

#### `GET /api/v1/plan/transfer-allocation`

**Query 参数：**

| 参数 | 对应 Filter | 说明 |
|------|-------------|------|
| `business_unit` | 事业部 | 默认「成人营养品事业部」 |
| `product_name` | 产品名称 | 模糊匹配 name 或 code |
| `base_warehouse` | 基地仓 | 如「武汉基地」 |
| `sales_warehouse` | 销售分仓 | 过滤「有该区域列且非空」的行（可选） |
| `product_series` | 产品系列 | `pro_series` 映射 |
| `adjust_date` | （隐藏，可选） | 默认 `MAX(adjust_date)` |

**Response `items[]` — 对齐 `TransferRow`：**

```json
{
  "id": "MOCK_WH_B04|MOCK_YLP001",
  "base_warehouse": "武汉基地",
  "product_name": "…",
  "product_code": "MOCK_YLP001",
  "monthly_inbound": 500,
  "normal_transit": 980,
  "transfer_transit": 650,
  "pending_inspect": 380,
  "pending_unpublish": 0,
  "qualified": 2800,
  "qualified_unpublish": 0,
  "available_qty": 4920,
  "regions": [
    {
      "region": "广州",
      "assign_qty": 120,
      "issued_not_shipped": 45,
      "pre_prod_stock_rate": 81.2,
      "post_prod_stock_rate": 100,
      "order_complete_rate": 0,
      "stock_days_after": 29,
      "next_month_days": 31
    }
  ]
}
```

**区域列表**：固定顺序与前端 `TRANSFER_REGIONS` 一致（10 城）；无 forward 行时该区域字段为 `null`，前端显示 `-`。

**`updated_at`**：当前快照 `adjust_date` + 固定时间或 `now()`。

**SQL 组装逻辑（service 层）**：

1. 从 `yl_base_warehouse_inventory_report` 取基地×产品行（filter + 最新 `adjust_date`）。
2. LEFT JOIN `yl_forward_transfer` 聚合基地侧 `from_available`、在途拆分。
3. 对每个 `to_site`，LEFT JOIN forward 行 + `yl_sales_warehouse_inventory_report` 取 `issued_not_dispatched`。
4. Pivot 为 `regions[]`；区域名 = `map_warehouse_to_region(to_site_name)`。

---

### 6.4 计划中心 Tab2 — 全国库存监控

#### `GET /api/v1/plan/national-inventory`

**Query 参数：**

| 参数 | 对应 Filter |
|------|-------------|
| `date` | 日期 → `adjust_date` |
| `business_unit` | 事业部 |
| `product_name` | 产品名称 |
| `product_series` | 产品系列 |

**Response `items[]` — 对齐 `NationalInventoryRow`：**

```json
{
  "date": "2026-07-02",
  "series": "中老年",
  "product_name": "…",
  "product_code": "MOCK_YLP001",
  "total_inventory": 12580,
  "base_warehouses": {
    "武汉基地": 3200,
    "呼市基地": 1800
  },
  "sales_spot": { "兰州": 120, "武汉": 340 },
  "sales_unshipped": { "兰州": 12, "武汉": 54 },
  "sales_gaps": { "兰州": -42, "武汉": -54, "徐州": null }
}
```

**列维度**：

- `base_warehouses` keys：与前端 `BASE_WAREHOUSES` 对齐；YL 仅 4 基地时 **缺列填 `null`** 或 Phase B 改前端列配置跟 DB 一致（设计期推荐 **后端补 null，前端不变**）。
- `sales_*` keys：与前端 `SALES_CITIES`（17 城）对齐；从 `yl_sales_warehouse_inventory_report` pivot，`from_store_num_h` / `total_unship` / `order_gap`（或 `ship_gap`）。

**`total_inventory`**：Σ 基地合格 + 销仓合格（或含在途，需在文档/代码注释固定口径）。

---

### 6.5 履约中心 — 分仓补录单

#### `GET /api/v1/fulfillment/branch-replenishment`

**Query 参数：**

| 参数 | 说明 |
|------|------|
| `inbound_logic_warehouse` | 调入逻辑仓 |
| `outbound_logic_warehouse` | 调出逻辑仓 |
| `initial_ship_warehouse` | 初始发货仓 |
| `business_unit` | 事业部 |
| `status` | `全部` / `生效` / `作废` |
| `transfer_gen_status` | `全部` / `未生成` / `已生成` |
| `product_name` | 商品名称/编码 |
| `source_order_no` | 来源单号（精确或前缀） |
| `created_from` / `created_to` | ISO 日期（替代 UI 文本区间） |
| `updated_from` / `updated_to` | 同上 |
| `upstream_created_from` / `upstream_created_to` | 同上 |

**Response `items[]` — 对齐 `BranchReplenishmentOrder`：**

```json
{
  "id": "uuid",
  "transfer_order_no": "TS29…",
  "product_code": "10001234",
  "sku_code": "SKU-80001",
  "product_name": "…",
  "unit": "EA",
  "business_unit": "成人营养品事业部",
  "ecommerce_barcode": "690…",
  "merchant_order_no": "MO202607020001",
  "status": "生效",
  "transfer_gen_status": "未生成",
  "transfer_qty": 1200,
  "gross_weight_per_ton": 0.0052,
  "total_gross_weight_ton": 6.24,
  "net_weight_per_ton": 0.0048,
  "total_net_weight_ton": 5.76,
  "volume_m3": 0.012,
  "total_volume_m3": 14.4,
  "temp_zone": "常温",
  "initial_ship_warehouse": "天津基地仓一盘货仓",
  "outbound_logic_warehouse": "…",
  "transit_warehouse": "-",
  "inbound_logic_warehouse": "…",
  "source_order_no": "SR20260702001",
  "actions": {
    "split": true,
    "invalidate": true,
    "increase": true,
    "log": true
  }
}
```

**Response 附加 `totals`**（对齐前端合计行）：

```json
{
  "totals": {
    "transfer_qty": 5640,
    "total_gross_weight_ton": 21.45,
    "total_net_weight_ton": 19.78,
    "total_volume_m3": 42.06
  }
}
```

#### `POST /api/v1/fulfillment/branch-replenishment`

**用途**：前端「创建补录单」、未来 **yl-worker1 Agent tool** 调用。

**Request body（必填 subset）：**

```json
{
  "product_code": "10001234",
  "product_name": "伊利欣活中老年奶粉(听装)1x6x800g",
  "transfer_qty": 1200,
  "initial_ship_warehouse": "天津基地仓一盘货仓",
  "outbound_logic_warehouse": "天津基地仓一盘货仓",
  "inbound_logic_warehouse": "天津销售仓一盘货仓",
  "transit_warehouse": "-",
  "source_order_no": "SR202607020001",
  "merchant_order_no": "MO202607020001",
  "temp_zone": "常温",
  "business_unit": "成人营养品事业部"
}
```

**服务端生成**：

- `id`（UUID）
- `transfer_order_no`（规则：`TS` + 时间 + 随机，或 ULID）
- `status` = `生效`
- `transfer_gen_status` = `未生成`
- 重量/体积：按 `yl_product.weight` / `volume` × `transfer_qty` 计算（Mockup DB 可缓存 product 快照）
- `actions`：按 status 默认 `{ split: true, invalidate: true, increase: true, log: true }`

**Response `201`：** `{ "item": { …完整 BranchReplenishmentOrder } }`

#### `PATCH /api/v1/fulfillment/branch-replenishment/{id}`（Phase 2）

| 操作 | body 示例 |
|------|-----------|
| 作废 | `{ "status": "作废" }` |
| 标记已生成调拨单 | `{ "transfer_gen_status": "已生成" }` |

---

## 7. Mockup DB 表结构（履约）

```sql
CREATE TABLE mock_branch_replenishment_order (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_order_no VARCHAR(64) NOT NULL UNIQUE,
    product_code VARCHAR(32) NOT NULL,
    sku_code VARCHAR(32),
    product_name VARCHAR(255) NOT NULL,
    unit VARCHAR(8) NOT NULL DEFAULT 'EA',
    business_unit VARCHAR(64) NOT NULL,
    ecommerce_barcode VARCHAR(32),
    merchant_order_no VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT '生效',
    transfer_gen_status VARCHAR(16) NOT NULL DEFAULT '未生成',
    transfer_qty NUMERIC(15,3) NOT NULL,
    gross_weight_per_ton NUMERIC(15,6),
    total_gross_weight_ton NUMERIC(15,3),
    net_weight_per_ton NUMERIC(15,6),
    total_net_weight_ton NUMERIC(15,3),
    volume_m3 NUMERIC(15,6),
    total_volume_m3 NUMERIC(15,3),
    temp_zone VARCHAR(16),
    initial_ship_warehouse VARCHAR(128),
    outbound_logic_warehouse VARCHAR(128),
    transit_warehouse VARCHAR(128),
    inbound_logic_warehouse VARCHAR(128),
    source_order_no VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    upstream_created_at TIMESTAMPTZ
);

CREATE INDEX idx_mock_bro_status ON mock_branch_replenishment_order(status);
CREATE INDEX idx_mock_bro_inbound ON mock_branch_replenishment_order(inbound_logic_warehouse);
```

首期 seed：导入 `mockData.ts` 中 5 条 `branchReplenishmentOrders`。

---

## 8. 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `YL_DATABASE_URL` | Phase B | Neon Postgres 只读（计划 Tab） |
| `MOCKUP_DATABASE_URL` | 是 | 履约写库 + 可选 seed |
| `DATA_SOURCE` | 否 | `yl`（默认）\| `seed`（计划 Tab 读 mock 表） |
| `MOCKUP_CORS_ORIGINS` | 是 | 前端 origin |
| `MOCKUP_API_KEY` | 否 | 保护 POST |
| `FLASK_ENV` | 否 | `development` / `production` |
| `DEFAULT_BUSINESS_UNIT` | 否 | 默认 `成人营养品事业部` |
| `DEFAULT_BUSINESS_CODE` | 否 | 默认 `CRYYBU` |

---

## 9. 部署

### 9.1 本地

```bash
cd yl-scm-mockup-api
uv sync
cp .env.example .env
uv run flask --app wsgi:app run --port 5001
```

前端 `.env`：

```
VITE_MOCKUP_API_BASE_URL=http://localhost:5001/api/v1
```

### 9.2 Vercel

- Root：`yl-scm-mockup-api`
- Build：安装依赖即可（无前端 build）
- Env：配置 `MOCKUP_DATABASE_URL`、`YL_DATABASE_URL`（可选）、`MOCKUP_CORS_ORIGINS`
- `vercel.json` 示例：

```json
{
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
}
```

---

## 10. 实施阶段

| 阶段 | 范围 | 数据 |
|------|------|------|
| **Phase A** | Meta + 履约 GET/POST + 计划 Tab seed 列表 | Mockup DB seed = `mockData.ts`；Filter 生效 |
| **Phase B** | 计划 Tab 切 YL 只读 SQL | `YL_DATABASE_URL` + 名称映射层 |
| **Phase C** | 补录单 PATCH、Agent tool 注册 | platform backend 新增 tool 指向 mockup API |

---

## 11. 前端对接清单

| 改动 | 文件 |
|------|------|
| 新增 API client（与 Nova client 分离） | `src/api/mockupClient.ts` |
| FilterPanel 搜索/重置触发 fetch | `FilterPanel.tsx` + 各 Tab |
| Tab 数据源 `useState` + `useEffect` | 3 个 Tab 组件 |
| 环境变量 | `VITE_MOCKUP_API_BASE_URL` |

Nova（`VITE_API_BASE_URL` → platform `:8000`）**保持不变**。

---

## 12. 附录：区域 / 仓名映射（Tab1）

后端维护 `config/region_map.yaml`（或 DB 表），示例：

```yaml
# yl_warehouse.site_name suffix → UI region label
"广州销售仓": "广州"
"合肥销售仓": "合肥"
"呼市销售仓": "呼市"
# UI 有而 YL 种子暂无的 region → 无 forward 行，返回 null
"自贡": null
"南京": null
```

正向分货 pivot 时 **UI 列顺序固定**，DB 有则填值，无则 `null`。

---

## 13. 附录：与 Agent 的关系

| 能力 | 服务 |
|------|------|
| 供应链分析、调拨建议、查 YL 报表 | platform `yl-worker1` + MCP + `YL_DATABASE_URL` |
| **创建履约补录单** | **本 API** `POST /fulfillment/branch-replenishment` |

Agent 不应写 YL 只读库；补录单写入 Mockup DB 即可被履约 Tab 展示。

未来可在 `yl-worker1` 增加 tool（HTTP 调用 mockup API），与本文 POST 契约一致。
