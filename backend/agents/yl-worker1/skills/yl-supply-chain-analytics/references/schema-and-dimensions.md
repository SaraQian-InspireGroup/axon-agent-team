# YL 供应链 schema 与分析维度

## 表清单（`yl_` 前缀）

| 表 | 中文 | 粒度 | 典型时间键 |
|----|------|------|------------|
| `yl_product` | 产品主数据 | SKU | — |
| `yl_warehouse` | 仓主数据 | 仓 | — |
| `yl_sales_plan` | 销售计划 | 仓×品×月 | `ds`, `plan_year`, `plan_month` |
| `yl_actual_sales` | 实际销量 | 仓×品×月 | `ds`, `sell_year`, `sell_month` |
| `yl_spot_inventory` | 现货库存 | 仓×品×批次 | `ds`, `produce_date` |
| `yl_transit_inventory` | 在途库存 | 流向×品 | `ds` |
| `yl_big_date_inventory` | 大日期库存 | 仓×品 | — |
| `yl_base_warehouse_inventory_report` | 基地仓监控报表 | 基地×品×日 | `adjust_date` |
| `yl_sales_warehouse_inventory_report` | 销售仓监控报表 | 销仓×品×日 | `adjust_date` |
| `yl_national_sales_warehouse_inventory_report` | 全国销售仓大盘 | 品×日（全国汇） | `adjust_date` |
| `yl_lateral_transfer` | 横向调拨 | 调拨单 | `adjust_date` |
| `yl_forward_transfer` | 正向调拨 | 调拨单 | `adjust_date` |
| `yl_wms_waybill` | WMS 运单 | 运单 | — |
| `yl_tms_gps` | TMS GPS | 轨迹点 | `location_time` |

## JOIN 键（通用）

```
product_code  →  yl_product.product_code
site_code     →  yl_warehouse.site_code
from_site_code / to_site_code  →  yl_warehouse.site_code
```

报表与明细对齐：`product_code` + `from_site_code`（或 `site_code`）+ **同一业务日**（`adjust_date` ≈ `ds`）。

## 仓类型

| `site_type` | 含义 |
|-------------|------|
| 0 | 基地仓 |
| 1 | 销售分仓 |

## 指标词典（场景 1 及相关）

| 业务名 | 常见列 | 口径说明 |
|--------|--------|----------|
| 可发量 / 合格现货 | `from_store_num_h`, `store_num`(status=合格), `invetory_deduct_sum` | 报表用合格现货；抵扣后库存已扣未执行调拨 |
| 待检现货 | `from_store_num_d` | 不可直接当作可发 |
| 在途 | `from_store_transit`, `store_transit` | 含待检+合格在途（见列注释） |
| 未发订单 | `total_unship`, `unshipped_orders`, `available_quantity`(actual_sales) | 报表 vs 销量表字段名不同 |
| 发货缺口 | `ship_gap` | 现货 − 未发（报表已算） |
| 订单缺口 | `order_gap` | 现货 + 在途 − 未发 |
| 日均计划 | `avg_plan_num`, `next_avg_plan_num` | 件/天 |
| 14 日需求 | `avg_plan_num * 14` | 无独立列时衍生 |
| 7 日需求 | `avg_plan_num * 7` | 紧急缺口窗口 |
| 库存天数 DOS | 报表无独立列时：`(from_store_num_h + from_store_transit) / NULLIF(avg_plan_num, 0)` | 完整口径含「已分配」时用业务方定义 |
| 基地可分配量 | `from_available`(forward_transfer), 基地合格+待检汇总 | 正向调拨决策用 |
| 销售完成率 | `sell_completion_rate` | 字符串百分比 |
| 订单完成率 | `order_completion_rate` | (未发+累出)/计划 |
| 大日期数量 | `big_date_num`, `xs_big_date_num`, `jd_big_date_num` | 销仓/基地/监控表 |

## 可分析维度矩阵

### 1. 地理 / 仓网

- 全国汇总（`national_*`）
- 单销售仓（`sales_warehouse_*` + `site_code`）
- 单基地仓（`base_warehouse_*`）
- 同城双仓（基地+销售，如天津、武汉、呼市——用 `site_name` 或 `remark` 关联）
- 在途流向（`from_site` → `to_site`）

### 2. 品项

- SKU：`product_code`
- 系列：`pro_series`
- 品牌：`brand`（经 `yl_product`）
- 包装：`pack_type`（听装/盒装）

### 3. 时间

- 监控日快照：`adjust_date`, `ds`
- 计划月：`plan_year`, `plan_month`
- 销量月：`sell_year`, `sell_month`
- 批次：`produce_date`（库龄 = 快照日 − 生产日期）

### 4. 供需与缺口

- 全国：可分配货源 vs 14 日需求
- 分仓：缺口量、分级、排名
- 完成率偏离：计划 vs 销量 vs 出库

### 5. 库存结构

- 合格 / 待检 / 礼盒
- 抵扣前 vs 抵扣后（`store_num` vs `invetory_deduct_sum`）
- 大日期占比

### 6. 物流与执行

- 在途量、已下发未发（`issued_not_dispatched`）
- 正向/横向调拨单及建议量 vs 下发量
- TMS 轨迹（辅助 ETA 叙述，数据稀疏时勿过度推断）

### 7. 渠道（报表层）

- 区域出货 `out_put_area`
- 电商出货 `out_put_ec`
- 电商询单 `ec_inquiry_cnt`

## 数据覆盖检查（分析前建议）

```sql
-- 最新监控快照日期
SELECT MAX(adjust_date) AS latest_report_date
FROM yl_national_sales_warehouse_inventory_report;

-- 各表行数与日期范围（示例）
SELECT 'sales_plan' AS tbl, COUNT(*) AS cnt, MIN(ds) AS min_ds, MAX(ds) AS max_ds
FROM yl_sales_plan
UNION ALL
SELECT 'spot_inventory', COUNT(*), MIN(ds), MAX(ds) FROM yl_spot_inventory;
```

## 组织边界提醒

- 业务文档：不含促销品、礼盒；分析常规补货时忽略 `*_lh_*` 礼盒列除非用户明确要求。
- Mock 数据产品编码前缀 `MOCK_YLP*` — 不影响分析逻辑。
