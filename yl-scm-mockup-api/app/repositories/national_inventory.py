"""Tab2 全国库存监控 — YL 只读 SQL（base_report + sales_report）."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db.yl import yl_connection

SNAPSHOT_SQL = """
SELECT COALESCE(%(adjust_date)s::date, (
    SELECT MAX(adjust_date) FROM yl_sales_warehouse_inventory_report
    WHERE business_code = %(business_code)s
)) AS d
"""

PRODUCTS_SQL = """
WITH snapshot AS (
    SELECT COALESCE(%(adjust_date)s::date, (
        SELECT MAX(adjust_date) FROM yl_sales_warehouse_inventory_report
        WHERE business_code = %(business_code)s
    )) AS d
)
SELECT DISTINCT
    sr.product_code,
    sr.product_name,
    sr.pro_series,
    snap.d AS snapshot_date
FROM yl_sales_warehouse_inventory_report sr
CROSS JOIN snapshot snap
WHERE sr.business_code = %(business_code)s
  AND sr.adjust_date = snap.d
  AND (%(product_series)s::text IS NULL OR sr.pro_series ILIKE %(product_series_pattern)s)
  AND (%(product_query)s::text IS NULL OR (
        sr.product_name ILIKE %(product_query_pattern)s
        OR sr.product_code ILIKE %(product_query_pattern)s
  ))
ORDER BY sr.product_name, sr.product_code
"""

BASE_ROWS_SQL = """
WITH snapshot AS (
    SELECT COALESCE(%(adjust_date)s::date, (
        SELECT MAX(adjust_date) FROM yl_sales_warehouse_inventory_report
        WHERE business_code = %(business_code)s
    )) AS d
)
SELECT
    b.product_code,
    b.from_site_code,
    b.from_site_name,
    b.from_store_num_h
FROM yl_base_warehouse_inventory_report b
CROSS JOIN snapshot snap
WHERE b.business_code = %(business_code)s
  AND b.adjust_date = snap.d
  AND (%(product_series)s::text IS NULL OR b.pro_series ILIKE %(product_series_pattern)s)
  AND (%(product_query)s::text IS NULL OR (
        b.product_name ILIKE %(product_query_pattern)s
        OR b.product_code ILIKE %(product_query_pattern)s
  ))
"""

SALES_ROWS_SQL = """
WITH snapshot AS (
    SELECT COALESCE(%(adjust_date)s::date, (
        SELECT MAX(adjust_date) FROM yl_sales_warehouse_inventory_report
        WHERE business_code = %(business_code)s
    )) AS d
)
SELECT
    sr.product_code,
    sr.from_site_code,
    sr.from_site_name,
    sr.from_store_num_h,
    sr.total_unship,
    sr.order_gap
FROM yl_sales_warehouse_inventory_report sr
CROSS JOIN snapshot snap
WHERE sr.business_code = %(business_code)s
  AND sr.adjust_date = snap.d
  AND (%(product_series)s::text IS NULL OR sr.pro_series ILIKE %(product_series_pattern)s)
  AND (%(product_query)s::text IS NULL OR (
        sr.product_name ILIKE %(product_query_pattern)s
        OR sr.product_code ILIKE %(product_query_pattern)s
  ))
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
    }


def fetch_products(params: dict[str, Any]) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(PRODUCTS_SQL, params)
            return list(cur.fetchall())


def fetch_base_rows(params: dict[str, Any]) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(BASE_ROWS_SQL, params)
            return list(cur.fetchall())


def fetch_sales_rows(params: dict[str, Any]) -> list[dict[str, Any]]:
    with yl_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SALES_ROWS_SQL, params)
            return list(cur.fetchall())
