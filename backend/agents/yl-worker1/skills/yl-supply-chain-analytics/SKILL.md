---
name: yl-supply-chain-analytics
description: 伊利奶粉分仓补货供应链只读分析：全国/分仓供需缺口、库存天数、计划达成、大日期与在途、仓间均衡、调拨追溯。用户问缺货、压仓、补货、分货、库存监控、DOS、发货缺口、全国货源、基地仓可分配量、横向调拨时使用。只读 YL 库；回复语言跟随用户。
---

# 伊利奶粉供应链分析

## 与 Agent 系统 Prompt 的分工

| 层 | 位置 | 内容 |
|----|------|------|
| **角色与对外表述** | `agents/yl-worker1/system_prompt.md` | 读者画像、业务语言、禁止泄露实现细节 |
| **运行时** | `agents/yl-worker1/profile.yaml` | 只读 MCP、`YL_DATABASE_URL`、**必须加载本 Skill** |
| **方法与数据（对内）** | 本 Skill + `references/` | 表结构、指标口径、SQL 片段——**仅供查数，勿写入用户可见正文** |

触发本 Skill 后，分析原则与查数范式以本文与 references 为准；**回复正文遵守 system prompt 的「对外沟通铁律」**。

## 分析哲学（高阶原则）

补货分析的本质是 **在正确的时间、把正确数量的货、放在最接近真实需求的仓**，并在效率、周转、新鲜度、订单满足之间取平衡。不要把它降格为「跑一张固定报表」——应先理解用户问的是 **供给够不够、分布匀不匀、风险在哪、动没动起来** 中的哪一类，再选粒度与数据源。

### 核心原则

1. **供需先于库存**：先看需求窗口内的缺口，再看绝对库存高低；高库存不等于安全（可能是错配），低库存加在途可能已缓解。
2. **分层视角**：全国汇总 → 基地仓货源 → 销售分仓履约 → 批次/日期结构；上层回答「总盘子够不够」，下层回答「谁缺谁压」。
3. **动静态结合**：现货是当下能力，在途是近期能力，计划/销量是消耗速度；三者合看才能算库存天数与缺口。
4. **推式 vs 拉式信号**：计划完成率低但销量高 → 推式分货滞后；备货率高但出库低 → 推式过量；用 **计划、销量、出库、未发订单** 交叉验证，勿单指标下结论。
5. **新鲜度是硬约束**：奶粉场景下，大日期/长库龄与缺货同等重要；分析库存结构时并看 **合格/待检、生产日期、大日期监控**。
6. **探索优先于死记**：references 提供维度地图与 SQL 片段；**每次分析仍应** `list_tables` / `describe_table` / `get_schema` 核实列名与注释，再写 SQL。片段是 few-shot，不是唯一路径。

### 默认可调业务阈值（用户未指定时）

| 信号 | 参考逻辑 | 对外称 |
|------|----------|--------|
| 紧急缺口 | 可发+在途 < 近 **7** 日需求 **且** 库存天数 < **7** | 红色 / 紧急补货 |
| 常规缺口 | 库存天数 **7–14** 天 | 黄色 / 常规补货 |
| 压仓预警 | 库存天数 > **60** 天 **且** 无促销消化计划（数据中若无促销字段，注明「需业务确认是否有促销」） | 蓝色 / 积压预警 |

需求窗口默认：**14 日**销售计划（`avg_plan_num × 14` 或报表已有计划字段）；7 日窗口用 `× 7`。DOS 口径：`(现货合格 + 在途 + 已分配未发调拨) / 日均计划`，优先用报表已算字段，缺失时再按列注释自行推导并在口径段说明。

## 数据源分层

| 层级 | 表（前缀 `yl_`） | 定位 |
|------|------------------|------|
| **主数据** | `product`, `warehouse` | 品、仓、品牌/系列、基地 vs 销售 |
| **计划与实绩** | `sales_plan`, `actual_sales` | 需求输入、销量、未发、出库 |
| **库存明细** | `spot_inventory`, `transit_inventory`, `big_date_inventory` | 批次现货、在途流向、大日期 |
| **监控报表（预聚合）** | `national_sales_warehouse_inventory_report`, `sales_warehouse_inventory_report`, `base_warehouse_inventory_report` | 全国/单仓/基地看板，缺口与完成率已算 |
| **调拨执行** | `lateral_transfer`, `forward_transfer` | 横向（销仓↔销仓）、正向（基地→销仓） |
| **物流追踪** | `wms_waybill`, `tms_gps` | 运单与在途轨迹（辅助，非主分析源） |

完整字段与维度矩阵见 [references/schema-and-dimensions.md](references/schema-and-dimensions.md)。

## 可分析维度（发散地图）

用户问题可映射到下列一个或多个切面；**不必每次全覆盖**，按意图选取。

| 切面 | 典型问题 | 主要数据源 |
|------|----------|------------|
| **全国供需平衡** | 全国货源够吗？总缺口多少？ | 全国报表、基地报表、计划汇总 |
| **分仓缺口分级** | 哪些仓要紧急补货？哪些压仓？ | 销售仓报表、现货+在途+计划 |
| **需求与履约** | 计划达成、未发订单、发货缺口 | 销售仓报表、`actual_sales` |
| **基地货源与可分配量** | 基地还有多少可分给销仓？ | 基地报表、`forward_transfer.from_available` |
| **仓间旱涝不均** | 谁缺谁余？可横向调拨吗？ | 多仓报表对比、`lateral_transfer` |
| **在途与补货在途** | 货在路上吗？何时缓解？ | `transit_inventory`、报表 `from_store_transit` |
| **新鲜度与大日期** | 哪些批次风险高？ | `big_date_inventory`、`spot_inventory.produce_date` |
| **库存结构** | 待检 vs 合格、抵扣后库存 | 现货/报表 `from_store_num_d/h` |
| **渠道出货结构** | 线下 vs 电商出货占比 | 报表 `out_put_area` / `out_put_ec` |
| **品项/系列/品牌** | 哪个 SKU/系列拖后腿？ | `product` + 各事实表 |
| **调拨追溯** | 已下发哪些正向/横向调拨？ | `forward_transfer`, `lateral_transfer` |
| **时间趋势** | 本月 vs 下月计划、销量走势 | `sales_plan` 多期、`actual_sales` |

各切面 SQL 片段见 references（按需加载，勿机械套全流程）。

## 工作流选择（意图 → 参考）

| 用户意图 | 参考 |
|----------|------|
| 全国全景、货源 vs 需求、分级缺口清单 | [supply-demand-gaps.md](references/supply-demand-gaps.md) |
| 计划达成、未发订单、推式/拉式偏离 | [demand-fulfillment.md](references/demand-fulfillment.md) |
| 大日期、库龄、待检/合格结构 | [inventory-freshness.md](references/inventory-freshness.md) |
| 仓间对比、调拨配对、均衡机会 | [cross-warehouse-balance.md](references/cross-warehouse-balance.md) |
| 表关系、JOIN 键、快照对齐 | [drilldown-joins.md](references/drilldown-joins.md) |
| 字段含义、维度矩阵、数据覆盖检查 | [schema-and-dimensions.md](references/schema-and-dimensions.md) |

## 执行顺序

1. **理解业务问题**：范围（全国/仓/品/系列）、时间、用户关心的决策（补货/调拨/监控）
2. **探索 schema**（自由模式）：`list_tables` → 对候选表 `describe_table` / `get_schema`；确认最新 `adjust_date` 或 `ds`
3. **选数据源**：优先用 **已聚合报表** 回答缺口/完成率；需要批次、流向、历史时再下钻明细表
4. **`query_data`**：必须带完整非空 `SELECT`；复用 reference 片段并按实际列名调整
5. **解读与分级**：按原则做红/黄/蓝或业务自定义分级；数字与建议分开表述
6. **可视化（按需）**：图表能显著帮助理解时再 `suggest_visualization`（`ranking` / `matrix` / `trend` / `auto`）

## 可视化（按需 suggest_visualization）

SQL 成功后平台只缓存结果，不自动出图。值得可视化时再调用；同轮多次 SQL 先 `list_sql_results` 取 `source_call_id`。

| 场景 | intent |
|------|--------|
| 分仓缺口排名、压仓 TOP | `ranking` |
| 系列×区域、仓×品矩阵 | `matrix` |
| 计划 vs 销量趋势 | `trend` |
| 全国汇总单指标 | `none` 或文字即可 |

## 过滤与口径惯例

- 主数据：`yl_product.is_delete = 0`（若列存在）
- 仓类型：`yl_warehouse.site_type` — `0` 基地仓，`1` 销售仓
- 快照：报表用 `adjust_date = (SELECT MAX(adjust_date) FROM …)` 或用户指定日
- 礼盒：`from_store_num_lh_*` 组织边界下通常为 0；分析常规品可忽略
- 百分比字段（如 `order_completion_rate`）库内可能是字符串 `'88.5%'`；排序/过滤时 `REPLACE(..., '%', '')::numeric`

## 输出格式（用户可见）

结构对齐 system prompt；下列为内容要点，**勿用表名/列名/SQL**。

### 摘要
- 快照日期、分析范围、2–3 条核心结论

### 供需与缺口（若相关）
- 全国或分仓：可发+在途 vs 需求、缺口量、红/黄/蓝分级清单

### 风险与结构（若相关）
- 大日期、长库龄、待检占比、仓间不均衡对

### 分析口径（可选）
- 例：「截至 6 月 15 日监控快照」「需求按近 14 日日均计划折算」「含在途未含待检」

### 建议的下一步
- 紧急正向补货、常规补货、横向调拨、促销消化、需人工核实项

### 对内 ↔ 对外 用语对照

| 对内 | 对用户说 |
|------|----------|
| `yl_national_sales_warehouse_inventory_report` | 全国销售仓库存监控看板 |
| `ship_gap` / `order_gap` | 发货缺口 / 订单缺口（现货±在途 vs 未发） |
| `avg_plan_num × 14` | 近 14 日销售计划需求 |
| `from_store_num_h` | 合格现货库存 |
| `from_available` | 基地仓可分配量 |
| `site_type = 1` | 销售分仓 |

## 禁止

- 不要 INSERT/UPDATE/DELETE
- 不要假设固定「场景一流程」；缺口识别是能力之一，不是唯一任务
- 不要在无 schema 确认时硬编码可能不存在的列

## 场景能力自检（场景 1：全国货源与需求缺口全局识别）

本 Skill **覆盖** 场景 1 的期望能力，且不限于此：

| 场景 1 期望 | Skill 如何覆盖 |
|-------------|----------------|
| 拉取仓网实时数据、基地/销仓/订单交叉对比 | 分层数据源 + [drilldown-joins.md](references/drilldown-joins.md) + 自由 schema 探索 |
| 批量识别缺货/压仓风险、全国供需全景 | [supply-demand-gaps.md](references/supply-demand-gaps.md) 全国汇总 + 分仓分级 |
| 产出分级缺口预警（红/黄/蓝） | 本文「默认可调业务阈值」+ 分仓 DOS/缺口 SQL |
| 产出积压预警表 | 蓝色阈值 + [inventory-freshness.md](references/inventory-freshness.md) |
| 全局：基地可分配+在途 vs 全国 14 日需求 | 全国/基地报表 + 计划汇总片段 |
| 分仓：可发+在途 vs 7 日需求、DOS | 销售仓报表 + 衍生计算 |
| 核心字段：可发量、需求量、DOS、基地可分配、未发订单、在途 | [schema-and-dimensions.md](references/schema-and-dimensions.md) 指标词典 |

**同时支持** 场景 2（大日期）、场景 3（调拨/in-transit）、计划偏离、渠道结构等——见维度地图，无需为每个场景单独写 Skill。
