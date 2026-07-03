"""Tab2 全国库存监控 — pivot 组装与 DTO 映射."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from app.config import load_region_config, settings
from app.repositories import national_inventory as repo
from app.schemas.national_inventory import NationalInventoryListResponse, NationalInventoryRowDTO
from app.utils.parsers import round_qty, to_float


def _national_columns() -> tuple[list[str], list[str]]:
    cfg = load_region_config()
    ni = cfg.get("national_inventory") or {}
    base_cols = list(ni.get("base_columns") or [])
    sales_cols = list(ni.get("sales_columns") or [])
    return base_cols, sales_cols


def _base_column_label(site_name: str) -> str | None:
    cfg = load_region_config()
    labels = cfg.get("base_warehouse_labels") or {}
    if site_name in labels:
        return labels[site_name]
    return None


def _sales_column_label(site_name: str) -> str | None:
    cfg = load_region_config()
    labels = cfg.get("sales_warehouse_labels") or {}
    if site_name in labels:
        return labels[site_name]
    return None


def _empty_column_map(columns: list[str]) -> dict[str, float | None]:
    return {col: None for col in columns}


def list_national_inventory(
    *,
    business_unit: str | None = None,
    product_name: str | None = None,
    product_series: str | None = None,
    adjust_date: date | None = None,
) -> NationalInventoryListResponse:
    business_code = settings.default_business_code
    base_columns, sales_columns = _national_columns()

    params = repo.build_params(
        business_code=business_code,
        adjust_date=adjust_date,
        product_series=product_series,
        product_query=product_name,
    )

    products = repo.fetch_products(params)
    if not products:
        return NationalInventoryListResponse(
            items=[],
            total=0,
            updated_at=_format_updated_at(adjust_date),
            base_warehouse_columns=base_columns,
            sales_city_columns=sales_columns,
            filters_applied=_filters_applied(business_unit, product_name, product_series, adjust_date),
        )

    snapshot_date = products[0].get("snapshot_date")
    params["adjust_date"] = snapshot_date

    base_rows = repo.fetch_base_rows(params)
    sales_rows = repo.fetch_sales_rows(params)

    base_by_product: dict[str, dict[str, float | None]] = {}
    for row in base_rows:
        label = _base_column_label(row["from_site_name"])
        if not label or label not in base_columns:
            continue
        code = row["product_code"]
        base_by_product.setdefault(code, _empty_column_map(base_columns))
        base_by_product[code][label] = round_qty(to_float(row.get("from_store_num_h")))

    sales_spot_by_product: dict[str, dict[str, float | None]] = {}
    sales_unship_by_product: dict[str, dict[str, float | None]] = {}
    sales_gap_by_product: dict[str, dict[str, float | None]] = {}

    for row in sales_rows:
        label = _sales_column_label(row["from_site_name"])
        if not label or label not in sales_columns:
            continue
        code = row["product_code"]
        sales_spot_by_product.setdefault(code, _empty_column_map(sales_columns))
        sales_unship_by_product.setdefault(code, _empty_column_map(sales_columns))
        sales_gap_by_product.setdefault(code, _empty_column_map(sales_columns))

        sales_spot_by_product[code][label] = round_qty(to_float(row.get("from_store_num_h")))
        sales_unship_by_product[code][label] = round_qty(to_float(row.get("total_unship")))
        sales_gap_by_product[code][label] = round_qty(to_float(row.get("order_gap")))

    items: list[NationalInventoryRowDTO] = []
    date_str = snapshot_date.isoformat() if snapshot_date else ""

    for product in products:
        code = product["product_code"]
        base_map = base_by_product.get(code, _empty_column_map(base_columns))
        spot_map = sales_spot_by_product.get(code, _empty_column_map(sales_columns))
        unship_map = sales_unship_by_product.get(code, _empty_column_map(sales_columns))
        gap_map = sales_gap_by_product.get(code, _empty_column_map(sales_columns))

        base_total = sum(v for v in base_map.values() if v is not None)
        sales_total = sum(v for v in spot_map.values() if v is not None)
        total_inventory = round_qty(base_total + sales_total)

        items.append(
            NationalInventoryRowDTO(
                date=date_str,
                series=product.get("pro_series") or "",
                product_name=product.get("product_name") or code,
                product_code=code,
                total_inventory=total_inventory,
                base_warehouses=base_map,
                sales_spot=spot_map,
                sales_unshipped=unship_map,
                sales_gaps=gap_map,
            )
        )

    return NationalInventoryListResponse(
        items=items,
        total=len(items),
        updated_at=_format_updated_at(snapshot_date),
        base_warehouse_columns=base_columns,
        sales_city_columns=sales_columns,
        filters_applied=_filters_applied(business_unit, product_name, product_series, snapshot_date),
    )


def _format_updated_at(snapshot: date | None) -> str:
    if snapshot is None:
        tz = timezone(timedelta(hours=8))
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    return f"{snapshot.isoformat()} 08:17"


def _filters_applied(
    business_unit: str | None,
    product_name: str | None,
    product_series: str | None,
    adjust_date: date | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if business_unit or settings.default_business_unit:
        result["business_unit"] = business_unit or settings.default_business_unit
    if product_name:
        result["product_name"] = product_name
    if product_series:
        result["product_series"] = product_series
    if adjust_date:
        result["date"] = adjust_date.isoformat()
    return result
