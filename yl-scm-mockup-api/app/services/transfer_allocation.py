"""Tab1 正向分货 — 业务组装与 DTO 映射."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from app.config import load_region_config, settings
from app.repositories import transfer_allocation as repo
from app.schemas.transfer import RegionAllocationDTO, TransferListResponse, TransferRowDTO
from app.utils.parsers import parse_days, parse_rate, round_qty, to_float


def _base_label(site_name: str) -> str:
    cfg = load_region_config()
    labels = cfg.get("base_warehouse_labels") or {}
    return labels.get(site_name, site_name.replace("基地仓", "基地"))


def _region_for_warehouse(site_name: str) -> str | None:
    cfg = load_region_config()
    mapping = cfg.get("warehouse_to_region") or {}
    return mapping.get(site_name)


def _transfer_regions() -> list[str]:
    cfg = load_region_config()
    return list(cfg.get("transfer_regions") or [])


def resolve_base_site_code(base_warehouse: str | None, warehouses: list[dict]) -> str | None:
    if not base_warehouse or not base_warehouse.strip():
        return None
    label = base_warehouse.strip()
    cfg = load_region_config()
    labels = cfg.get("base_warehouse_labels") or {}
    # UI label → site_name
    for site_name, ui_label in labels.items():
        if ui_label == label or site_name.startswith(label.replace("基地", "")):
            for wh in warehouses:
                if wh["site_type"] == 0 and wh["site_name"] == site_name:
                    return wh["site_code"]
    for wh in warehouses:
        if wh["site_type"] == 0 and (
            wh["site_name"] == label
            or wh["site_name"].replace("基地仓", "基地") == label
        ):
            return wh["site_code"]
    return None


def resolve_sales_site_code(sales_warehouse: str | None, warehouses: list[dict]) -> str | None:
    if not sales_warehouse or not sales_warehouse.strip():
        return None
    label = sales_warehouse.strip()
    cfg = load_region_config()
    labels = cfg.get("sales_warehouse_labels") or {}
    for site_name, ui_label in labels.items():
        if ui_label == label:
            for wh in warehouses:
                if wh["site_type"] == 1 and wh["site_name"] == site_name:
                    return wh["site_code"]
    for wh in warehouses:
        if wh["site_type"] == 1 and (
            wh["site_name"] == label or wh["site_name"].replace("销售仓", "") == label
        ):
            return wh["site_code"]
    return None


def _build_region_map(
    forward_rows: list[dict[str, Any]],
    *,
    sales_site_filter: str | None,
) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    """(from_site_code, product_code) -> {region_label: metrics}."""
    result: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in forward_rows:
        if sales_site_filter and row["to_site_code"] != sales_site_filter:
            continue
        region = _region_for_warehouse(row["to_site_name"])
        if not region:
            continue
        key = (row["from_site_code"], row["product_code"])
        result.setdefault(key, {})[region] = row
    return result


def _region_dto(region: str, row: dict[str, Any] | None) -> RegionAllocationDTO:
    if row is None:
        return RegionAllocationDTO(region=region)
    trans = to_float(row.get("trans_num"))
    return RegionAllocationDTO(
        region=region,
        assign_qty=round_qty(trans) if trans is not None else "",
        issued_not_shipped=round_qty(to_float(row.get("issued_not_dispatched")) or 0),
        pre_prod_stock_rate=parse_rate(row.get("to_stock_rate_before")),
        post_prod_stock_rate=parse_rate(row.get("to_stock_rate_after")),
        order_complete_rate=parse_rate(row.get("to_order_completion_rate")) or 0,
        stock_days_after=parse_days(row.get("to_store_day_after")) or 0,
        next_month_days=parse_days(row.get("to_store_day_next")) or 0,
    )


def list_transfer_allocation(
    *,
    business_unit: str | None = None,
    product_name: str | None = None,
    base_warehouse: str | None = None,
    sales_warehouse: str | None = None,
    product_series: str | None = None,
    adjust_date: date | None = None,
) -> TransferListResponse:
    business_code = settings.default_business_code
    warehouses = repo.fetch_meta_warehouses(business_code)
    base_site_code = resolve_base_site_code(base_warehouse, warehouses)
    sales_site_code = resolve_sales_site_code(sales_warehouse, warehouses)

    params = repo.build_params(
        business_code=business_code,
        adjust_date=adjust_date,
        product_series=product_series,
        product_query=product_name,
        base_site_code=base_site_code,
        sales_site_code=None,
    )

    base_rows = repo.fetch_base_inventory_rows(params)
    if not base_rows:
        return TransferListResponse(
            items=[],
            total=0,
            updated_at=_format_updated_at(adjust_date),
            filters_applied=_filters_applied(
                business_unit, product_name, base_warehouse, sales_warehouse, product_series
            ),
        )

    snapshot_date = base_rows[0].get("snapshot_date")
    params["adjust_date"] = snapshot_date
    params["base_site_code"] = base_site_code
    forward_rows = repo.fetch_forward_region_rows(params)
    region_map = _build_region_map(forward_rows, sales_site_filter=sales_site_code)

    items: list[TransferRowDTO] = []
    region_order = _transfer_regions()

    for row in base_rows:
        key = (row["from_site_code"], row["product_code"])
        regions_by_label = region_map.get(key, {})
        regions = [_region_dto(r, regions_by_label.get(r)) for r in region_order]

        if sales_site_code:
            # 仅保留在筛选销售仓对应区域有 forward 行的基地×品项
            mapped = _region_for_warehouse(
                next(
                    (fr["to_site_name"] for fr in forward_rows if fr["to_site_code"] == sales_site_code),
                    "",
                )
            )
            if mapped and regions_by_label.get(mapped) is None:
                continue

        monthly = to_float(row.get("month_store_in"))
        items.append(
            TransferRowDTO(
                id=f"{row['from_site_code']}|{row['product_code']}",
                base_warehouse=_base_label(row["from_site_name"]),
                product_name=row["product_name"] or row["product_code"],
                product_code=row["product_code"],
                monthly_inbound=round_qty(monthly) if monthly is not None else "",
                normal_transit=round_qty(to_float(row.get("normal_transit")) or 0),
                transfer_transit=round_qty(to_float(row.get("transfer_transit")) or 0),
                pending_inspect=round_qty(to_float(row.get("pending_inspect")) or 0),
                pending_unpublish=round_qty(to_float(row.get("pending_unpublish")) or 0),
                qualified=round_qty(to_float(row.get("qualified")) or 0),
                qualified_unpublish=round_qty(to_float(row.get("qualified_unpublish")) or 0),
                available_qty=round_qty(to_float(row.get("available_qty")) or 0),
                regions=regions,
            )
        )

    updated = _format_updated_at(snapshot_date)
    return TransferListResponse(
        items=items,
        total=len(items),
        updated_at=updated,
        filters_applied=_filters_applied(
            business_unit, product_name, base_warehouse, sales_warehouse, product_series
        ),
    )


def _format_updated_at(snapshot: date | None) -> str:
    if snapshot is None:
        tz = timezone(timedelta(hours=8))
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    return f"{snapshot.isoformat()} 08:17"


def _filters_applied(
    business_unit: str | None,
    product_name: str | None,
    base_warehouse: str | None,
    sales_warehouse: str | None,
    product_series: str | None,
) -> dict[str, Any]:
    return {
        k: v
        for k, v in {
            "business_unit": business_unit or settings.default_business_unit,
            "product_name": product_name,
            "base_warehouse": base_warehouse,
            "sales_warehouse": sales_warehouse,
            "product_series": product_series,
        }.items()
        if v
    }
