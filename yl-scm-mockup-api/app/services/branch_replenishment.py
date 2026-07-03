"""履约中心分仓补录单 — 业务逻辑."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any

from app.config import load_fulfillment_config, settings
from app.repositories import branch_replenishment as repo
from app.repositories import product_lookup
from app.schemas.branch_replenishment import (
    BranchReplenishmentActionsDTO,
    BranchReplenishmentListResponse,
    BranchReplenishmentOrderDTO,
    BranchReplenishmentTotalsDTO,
    CreateBranchReplenishmentRequest,
    CreateBranchReplenishmentResponse,
    GenerateTransferResponse,
)


def _parse_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    return date.fromisoformat(value.strip())


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_logic_warehouse(name: str) -> str:
    label = name.strip()
    cfg = load_fulfillment_config()
    mapping = cfg.get("warehouse_logic_labels") or {}
    if label in mapping.values():
        return label
    return mapping.get(label, label)


def _mock_barcode(product_code: str) -> str:
    digits = sum(ord(c) for c in product_code)
    return f"690{digits % 10**9:09d}"


def _derive_actions(status: str, transfer_gen_status: str) -> BranchReplenishmentActionsDTO:
    active = status in ("草稿", "生效")
    return BranchReplenishmentActionsDTO(
        split=active and transfer_gen_status == "未生成",
        invalidate=active,
        increase=status == "生效",
        log=True,
    )


def _row_to_dto(row: dict[str, Any]) -> BranchReplenishmentOrderDTO:
    status = row.get("status") or "草稿"
    gen_status = row.get("transfer_gen_status") or "未生成"
    return BranchReplenishmentOrderDTO(
        id=str(row["id"]),
        transfer_order_no=row["transfer_order_no"],
        product_code=row["product_code"],
        sku_code=row.get("sku_code") or row["product_code"],
        product_name=row["product_name"],
        unit=row.get("unit") or "EA",
        business_unit=row["business_unit"],
        ecommerce_barcode=row.get("ecommerce_barcode"),
        merchant_order_no=row.get("merchant_order_no"),
        status=status,
        transfer_gen_status=gen_status,
        transfer_qty=_to_float(row.get("transfer_qty")),
        gross_weight_per_ton=_to_float(row.get("gross_weight_per_ton")),
        total_gross_weight_ton=_to_float(row.get("total_gross_weight_ton")),
        net_weight_per_ton=_to_float(row.get("net_weight_per_ton")),
        total_net_weight_ton=_to_float(row.get("total_net_weight_ton")),
        volume_m3=_to_float(row.get("volume_m3")),
        total_volume_m3=_to_float(row.get("total_volume_m3")),
        temp_zone=row.get("temp_zone") or "常温",
        initial_ship_warehouse=row.get("initial_ship_warehouse"),
        outbound_logic_warehouse=row.get("outbound_logic_warehouse"),
        transit_warehouse=row.get("transit_warehouse") or "-",
        inbound_logic_warehouse=row.get("inbound_logic_warehouse"),
        source_order_no=row.get("source_order_no"),
        planned_ship_at=_iso(row.get("planned_ship_at")),
        expected_arrival_at=_iso(row.get("expected_arrival_at")),
        shipping_remark=row.get("shipping_remark"),
        created_at=_iso(row.get("created_at")),
        updated_at=_iso(row.get("updated_at")),
        upstream_created_at=_iso(row.get("upstream_created_at")),
        actions=_derive_actions(status, gen_status),
    )


def _calc_physical(product: dict | None, transfer_qty: float) -> dict[str, float | None]:
    per_ton = _to_float(product.get("weight") if product else None, 0.001)
    volume_raw = product.get("volume") if product else None
    per_volume = _to_float(volume_raw, 0.01) if volume_raw not in (None, "") else 0.01
    qty = float(transfer_qty)
    return {
        "gross_weight_per_ton": per_ton,
        "total_gross_weight_ton": round(per_ton * qty, 3),
        "net_weight_per_ton": per_ton,
        "total_net_weight_ton": round(per_ton * qty, 3),
        "volume_m3": per_volume,
        "total_volume_m3": round(per_volume * qty, 3),
    }


def _new_transfer_order_no() -> str:
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    suffix = secrets.token_hex(24)
    return f"TS{ts}{suffix}"[:64]


def list_branch_replenishment(
    *,
    inbound_logic_warehouse: str | None = None,
    outbound_logic_warehouse: str | None = None,
    initial_ship_warehouse: str | None = None,
    business_unit: str | None = None,
    status: str | None = None,
    transfer_gen_status: str | None = None,
    product_name: str | None = None,
    source_order_no: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
    upstream_created_from: str | None = None,
    upstream_created_to: str | None = None,
) -> BranchReplenishmentListResponse:
    params = repo.build_list_params(
        inbound_logic_warehouse=inbound_logic_warehouse,
        outbound_logic_warehouse=outbound_logic_warehouse,
        initial_ship_warehouse=initial_ship_warehouse,
        business_unit=business_unit or settings.default_business_unit,
        status=status,
        transfer_gen_status=transfer_gen_status,
        product_name=product_name,
        source_order_no=source_order_no,
        created_from=_parse_date(created_from),
        created_to=_parse_date(created_to),
        updated_from=_parse_date(updated_from),
        updated_to=_parse_date(updated_to),
        upstream_created_from=_parse_date(upstream_created_from),
        upstream_created_to=_parse_date(upstream_created_to),
    )
    rows = repo.fetch_orders(params)
    items = [_row_to_dto(r) for r in rows]
    totals = BranchReplenishmentTotalsDTO(
        transfer_qty=sum(i.transfer_qty for i in items),
        total_gross_weight_ton=sum(i.total_gross_weight_ton or 0 for i in items),
        total_net_weight_ton=sum(i.total_net_weight_ton or 0 for i in items),
        total_volume_m3=sum(i.total_volume_m3 or 0 for i in items),
    )
    return BranchReplenishmentListResponse(
        items=items,
        total=len(items),
        updated_at=datetime.now(timezone.utc).isoformat(),
        totals=totals,
        filters_applied={k: v for k, v in params.items() if v is not None},
    )


def create_branch_replenishment(
    body: CreateBranchReplenishmentRequest,
) -> CreateBranchReplenishmentResponse:
    if body.transfer_qty <= 0:
        raise ValueError("调拨数量必须大于 0")

    product = product_lookup.fetch_product(body.product_code)
    if not product:
        raise ValueError(f"未找到商品主数据: {body.product_code}")

    physical = _calc_physical(product, body.transfer_qty)
    sku = (body.sku_code or body.product_code).strip()

    row = {
        "transfer_order_no": _new_transfer_order_no(),
        "product_code": body.product_code.strip(),
        "sku_code": sku,
        "product_name": product["product_name"],
        "unit": "EA",
        "business_unit": body.business_unit.strip(),
        "ecommerce_barcode": _mock_barcode(body.product_code),
        "merchant_order_no": body.merchant_order_no,
        "source_order_no": body.source_order_no,
        "status": "草稿",
        "transfer_gen_status": "未生成",
        "transfer_qty": body.transfer_qty,
        **physical,
        "temp_zone": body.temp_zone or "常温",
        "initial_ship_warehouse": _normalize_logic_warehouse(body.initial_ship_warehouse),
        "outbound_logic_warehouse": _normalize_logic_warehouse(body.outbound_logic_warehouse),
        "transit_warehouse": body.transit_warehouse or "-",
        "inbound_logic_warehouse": _normalize_logic_warehouse(body.inbound_logic_warehouse),
        "planned_ship_at": body.planned_ship_at,
        "expected_arrival_at": body.expected_arrival_at,
        "shipping_remark": body.shipping_remark,
    }
    inserted = repo.insert_order(row)
    return CreateBranchReplenishmentResponse(item=_row_to_dto(inserted))


def generate_transfer(*, ids: list[str]) -> GenerateTransferResponse:
    unique_ids = list(dict.fromkeys(i.strip() for i in ids if i.strip()))
    if not unique_ids:
        raise ValueError("ids 不能为空")

    existing = {str(r["id"]): r for r in repo.fetch_by_ids(unique_ids)}
    skipped: list[dict[str, str]] = []
    eligible: list[str] = []

    for oid in unique_ids:
        row = existing.get(oid)
        if not row:
            skipped.append({"id": oid, "reason": "记录不存在"})
            continue
        if row.get("transfer_gen_status") == "已生成":
            skipped.append({"id": oid, "reason": "已生成调拨单"})
            continue
        if row.get("status") not in ("草稿", "生效"):
            skipped.append({"id": oid, "reason": f"状态不可生成: {row.get('status')}"})
            continue
        eligible.append(oid)

    updated_rows = repo.generate_transfer_orders(eligible) if eligible else []
    items = [_row_to_dto(r) for r in updated_rows]
    return GenerateTransferResponse(
        updated_count=len(items),
        items=items,
        skipped=skipped,
    )
