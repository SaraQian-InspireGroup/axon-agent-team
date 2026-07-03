"""Tab1 正向分货 — YL 只读 SQL."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db.yl import yl_connection

# 基地库存行 + spot 聚合 + forward 在途/可发量
BASE_INVENTORY_SQL = """
WITH snapshot AS (
    SELECT COALESCE(%(adjust_date)s::date, (
        SELECT MAX(adjust_date) FROM yl_base_warehouse_inventory_report
        WHERE business_code = %(business_code)s
    )) AS d
),
spot_agg AS (
    SELECT
        si.site_code,
        si.product_code,
        SUM(CASE WHEN si.status = '待检' THEN COALESCE(si.store_num, 0) ELSE 0 END)
            AS pending_inspect,
        SUM(CASE WHEN si.status = '待检' THEN
            COALESCE(si.oms_dist_num, 0) + COALESCE(si.wms_dist_num, 0) + COALESCE(si.tms_dist_num, 0)
            ELSE 0 END) AS pending_unpublish,
        SUM(CASE WHEN si.status = '合格' THEN COALESCE(si.store_num, 0) ELSE 0 END)
            AS qualified,
        SUM(CASE WHEN si.status = '合格' THEN
            COALESCE(si.oms_dist_num, 0) + COALESCE(si.wms_dist_num, 0) + COALESCE(si.tms_dist_num, 0)
            ELSE 0 END) AS qualified_pre_occupy
    FROM yl_spot_inventory si
    CROSS JOIN snapshot snap
    WHERE si.site_type = 0
      AND si.is_delete = 0
      AND si.ds::date = snap.d
    GROUP BY si.site_code, si.product_code
),
forward_date AS (
    SELECT ft.adjust_date AS d
    FROM yl_forward_transfer ft
    CROSS JOIN snapshot snap
    WHERE ft.business_code = %(business_code)s
      AND date_trunc('month', ft.adjust_date) = date_trunc('month', snap.d)
    GROUP BY ft.adjust_date
    ORDER BY COUNT(*) DESC, ft.adjust_date DESC
    LIMIT 1
),
ft_agg AS (
    SELECT
        ft.from_site_code,
        ft.product_code,
        SUM(COALESCE(ft.from_store_transit, 0)) AS normal_transit,
        SUM(COALESCE(ft.from_store_transit_zt, 0)) AS transfer_transit,
        MAX(COALESCE(ft.from_available, 0)) AS available_qty
    FROM yl_forward_transfer ft
    CROSS JOIN forward_date fd
    WHERE ft.business_code = %(business_code)s
      AND ft.adjust_date = fd.d
    GROUP BY ft.from_site_code, ft.product_code
)
SELECT
    b.from_site_code,
    b.from_site_name,
    b.product_code,
    b.product_name,
    b.pro_series,
    b.month_store_in,
    b.big_date_num,
    COALESCE(s.pending_inspect, b.from_store_num_d, 0) AS pending_inspect,
    COALESCE(s.pending_unpublish, 0) AS pending_unpublish,
    COALESCE(s.qualified, b.from_store_num_h, 0) AS qualified,
    COALESCE(s.qualified_pre_occupy, 0) + COALESCE(b.big_date_num, 0) AS qualified_unpublish,
    COALESCE(ft.normal_transit, 0) AS normal_transit,
    COALESCE(ft.transfer_transit, 0) AS transfer_transit,
    COALESCE(ft.available_qty, 0) AS available_qty,
    snap.d AS snapshot_date,
    fd.d AS forward_date
FROM yl_base_warehouse_inventory_report b
CROSS JOIN snapshot snap
CROSS JOIN forward_date fd
LEFT JOIN spot_agg s
    ON s.site_code = b.from_site_code AND s.product_code = b.product_code
LEFT JOIN ft_agg ft
    ON ft.from_site_code = b.from_site_code AND ft.product_code = b.product_code
WHERE b.adjust_date = snap.d
  AND b.business_code = %(business_code)s
  AND (%(product_series)s::text IS NULL OR b.pro_series ILIKE %(product_series_pattern)s)
  AND (%(product_query)s::text IS NULL OR (
        b.product_name ILIKE %(product_query_pattern)s
        OR b.product_code ILIKE %(product_query_pattern)s
  ))
  AND (%(base_site_code)s::text IS NULL OR b.from_site_code = %(base_site_code)s)
ORDER BY b.from_site_name, b.product_name
"""

FORWARD_REGIONS_SQL = """
WITH snapshot AS (
    SELECT COALESCE(%(adjust_date)s::date, (
        SELECT MAX(adjust_date) FROM yl_base_warehouse_inventory_report
        WHERE business_code = %(business_code)s
    )) AS d
),
forward_date AS (
    SELECT ft.adjust_date AS d
    FROM yl_forward_transfer ft
    CROSS JOIN snapshot snap
    WHERE ft.business_code = %(business_code)s
      AND date_trunc('month', ft.adjust_date) = date_trunc('month', snap.d)
    GROUP BY ft.adjust_date
    ORDER BY COUNT(*) DESC, ft.adjust_date DESC
    LIMIT 1
)
SELECT
    ft.from_site_code,
    ft.product_code,
    ft.to_site_code,
    ft.to_site_name,
    ft.trans_num,
    ft.to_stock_rate_before,
    ft.to_stock_rate_after,
    ft.to_order_completion_rate,
    ft.to_store_day_after,
    ft.to_store_day_next,
    sw.issued_not_dispatched
FROM yl_forward_transfer ft
CROSS JOIN snapshot snap
CROSS JOIN forward_date fd
LEFT JOIN yl_sales_warehouse_inventory_report sw
    ON sw.from_site_code = ft.to_site_code
   AND sw.product_code = ft.product_code
   AND sw.adjust_date = snap.d
WHERE ft.business_code = %(business_code)s
  AND ft.adjust_date = fd.d
  AND (%(base_site_code)s::text IS NULL OR ft.from_site_code = %(base_site_code)s)
  AND (%(sales_site_code)s::text IS NULL OR ft.to_site_code = %(sales_site_code)s)
"""

META_FILTERS_SQL = """
SELECT DISTINCT pro_series
FROM yl_product
WHERE business_code = %(business_code)s
  AND pro_series IS NOT NULL AND pro_series <> ''
ORDER BY pro_series
"""

PRODUCTS_SQL = """
SELECT product_code, product_name
FROM yl_product
WHERE business_code = %(business_code)s
ORDER BY product_name
"""

WAREHOUSES_SQL = """
SELECT site_code, site_name, site_type
FROM yl_warehouse
WHERE business_code = %(business_code)s
ORDER BY site_type, sort, site_name
"""


def _like_pattern(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return f"%{value.strip()}%"


def build_params(
    *,
    business_code: str,
    adjust_date: date | None = None,
    product_series: str | None = None,
    product_query: str | None = None,
    base_site_code: str | None = None,
    sales_site_code: str | None = None,
) -> dict[str, Any]:
    series = product_series.strip() if product_series and product_series.strip() else None
    query = product_query.strip() if product_query and product_query.strip() else None
    return {
        "business_code": business_code,
        "adjust_date": adjust_date,
        "product_series": series,
        "product_series_pattern": series,
        "product_query": query,
        "product_query_pattern": _like_pattern(query),
        "base_site_code": base_site_code,
        "sales_site_code": sales_site_code,
    }


def fetch_base_inventory_rows(params: dict[str, Any]) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(BASE_INVENTORY_SQL, params)
            return list(cur.fetchall())


def fetch_forward_region_rows(params: dict[str, Any]) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(FORWARD_REGIONS_SQL, params)
            return list(cur.fetchall())


def fetch_meta_products(business_code: str) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(PRODUCTS_SQL, {"business_code": business_code})
            return list(cur.fetchall())


def fetch_meta_warehouses(business_code: str) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(WAREHOUSES_SQL, {"business_code": business_code})
            return list(cur.fetchall())


def fetch_meta_series(business_code: str) -> list[str]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(META_FILTERS_SQL, {"business_code": business_code})
            return [row["pro_series"] for row in cur.fetchall()]
