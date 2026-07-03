"""履约中心分仓补录单 — Mockup DB 读写."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.db.mockup import mockup_connection

LIST_SQL = """
SELECT *
FROM mock_branch_replenishment_order
WHERE (%(inbound_logic_warehouse)s::text IS NULL
       OR inbound_logic_warehouse = %(inbound_logic_warehouse)s)
  AND (%(outbound_logic_warehouse)s::text IS NULL
       OR outbound_logic_warehouse = %(outbound_logic_warehouse)s)
  AND (%(initial_ship_warehouse)s::text IS NULL
       OR initial_ship_warehouse = %(initial_ship_warehouse)s)
  AND (%(business_unit)s::text IS NULL OR business_unit = %(business_unit)s)
  AND (%(status)s::text IS NULL OR status = %(status)s)
  AND (%(transfer_gen_status)s::text IS NULL
       OR transfer_gen_status = %(transfer_gen_status)s)
  AND (%(product_pattern)s::text IS NULL
       OR product_code ILIKE %(product_pattern)s
       OR product_name ILIKE %(product_pattern)s)
  AND (%(source_order_no)s::text IS NULL
       OR source_order_no ILIKE %(source_order_pattern)s)
  AND (%(created_from)s::timestamptz IS NULL OR created_at >= %(created_from)s)
  AND (%(created_to)s::timestamptz IS NULL OR created_at < %(created_to)s)
  AND (%(updated_from)s::timestamptz IS NULL OR updated_at >= %(updated_from)s)
  AND (%(updated_to)s::timestamptz IS NULL OR updated_at < %(updated_to)s)
  AND (%(upstream_created_from)s::timestamptz IS NULL
       OR upstream_created_at >= %(upstream_created_from)s)
  AND (%(upstream_created_to)s::timestamptz IS NULL
       OR upstream_created_at < %(upstream_created_to)s)
ORDER BY created_at DESC, transfer_order_no
"""

INSERT_SQL = """
INSERT INTO mock_branch_replenishment_order (
    transfer_order_no, product_code, sku_code, product_name, unit, business_unit,
    ecommerce_barcode, merchant_order_no, source_order_no, status, transfer_gen_status,
    transfer_qty, gross_weight_per_ton, total_gross_weight_ton, net_weight_per_ton,
    total_net_weight_ton, volume_m3, total_volume_m3, temp_zone,
    initial_ship_warehouse, outbound_logic_warehouse, transit_warehouse,
    inbound_logic_warehouse, planned_ship_at, expected_arrival_at, shipping_remark
) VALUES (
    %(transfer_order_no)s, %(product_code)s, %(sku_code)s, %(product_name)s, %(unit)s,
    %(business_unit)s, %(ecommerce_barcode)s, %(merchant_order_no)s, %(source_order_no)s,
    %(status)s, %(transfer_gen_status)s, %(transfer_qty)s, %(gross_weight_per_ton)s,
    %(total_gross_weight_ton)s, %(net_weight_per_ton)s, %(total_net_weight_ton)s,
    %(volume_m3)s, %(total_volume_m3)s, %(temp_zone)s, %(initial_ship_warehouse)s,
    %(outbound_logic_warehouse)s, %(transit_warehouse)s, %(inbound_logic_warehouse)s,
    %(planned_ship_at)s, %(expected_arrival_at)s, %(shipping_remark)s
)
RETURNING *
"""

FETCH_BY_IDS_SQL = """
SELECT * FROM mock_branch_replenishment_order
WHERE id = ANY(%(ids)s::uuid[])
"""

GENERATE_TRANSFER_SQL = """
UPDATE mock_branch_replenishment_order
SET transfer_gen_status = '已生成',
    status = CASE WHEN status = '草稿' THEN '生效' ELSE status END,
    updated_at = now()
WHERE id = ANY(%(ids)s::uuid[])
  AND transfer_gen_status = '未生成'
  AND status IN ('草稿', '生效')
RETURNING *
"""


def _like_pattern(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return f"%{value.strip()}%"


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d, datetime.max.time())


def build_list_params(
    *,
    inbound_logic_warehouse: str | None = None,
    outbound_logic_warehouse: str | None = None,
    initial_ship_warehouse: str | None = None,
    business_unit: str | None = None,
    status: str | None = None,
    transfer_gen_status: str | None = None,
    product_name: str | None = None,
    source_order_no: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    updated_from: date | None = None,
    updated_to: date | None = None,
    upstream_created_from: date | None = None,
    upstream_created_to: date | None = None,
) -> dict[str, Any]:
    norm_status = None if not status or status.strip() in ("", "全部") else status.strip()
    norm_gen = (
        None
        if not transfer_gen_status or transfer_gen_status.strip() in ("", "全部")
        else transfer_gen_status.strip()
    )
    src = source_order_no.strip() if source_order_no and source_order_no.strip() else None
    return {
        "inbound_logic_warehouse": inbound_logic_warehouse or None,
        "outbound_logic_warehouse": outbound_logic_warehouse or None,
        "initial_ship_warehouse": initial_ship_warehouse or None,
        "business_unit": business_unit or None,
        "status": norm_status,
        "transfer_gen_status": norm_gen,
        "product_pattern": _like_pattern(product_name),
        "source_order_no": src,
        "source_order_pattern": f"{src}%" if src else None,
        "created_from": datetime.combine(created_from, datetime.min.time()) if created_from else None,
        "created_to": _end_of_day(created_to) if created_to else None,
        "updated_from": datetime.combine(updated_from, datetime.min.time()) if updated_from else None,
        "updated_to": _end_of_day(updated_to) if updated_to else None,
        "upstream_created_from": (
            datetime.combine(upstream_created_from, datetime.min.time())
            if upstream_created_from
            else None
        ),
        "upstream_created_to": _end_of_day(upstream_created_to) if upstream_created_to else None,
    }


def fetch_orders(params: dict[str, Any]) -> list[dict[str, Any]]:
    with mockup_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(LIST_SQL, params)
            return list(cur.fetchall())


def fetch_by_ids(ids: list[str]) -> list[dict[str, Any]]:
    with mockup_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(FETCH_BY_IDS_SQL, {"ids": ids})
            return list(cur.fetchall())


def insert_order(row: dict[str, Any]) -> dict[str, Any]:
    with mockup_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_SQL, row)
            inserted = cur.fetchone()
        conn.commit()
        return inserted


def generate_transfer_orders(ids: list[str]) -> list[dict[str, Any]]:
    with mockup_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(GENERATE_TRANSFER_SQL, {"ids": ids})
            updated = list(cur.fetchall())
        conn.commit()
        return updated
