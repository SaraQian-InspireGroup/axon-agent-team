"""Serialize and load MDM catalog snapshots for migrations and seed scripts."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.mdm.excel_import import (
    MdmCatalogSnapshot,
    PackageRecord,
    ServiceRecord,
    default_bvi_xlsx_path,
    parse_bvi_catalog,
)

DEFAULT_BVI_JSON = Path(__file__).resolve().parent / "data" / "bvi_catalog.json"


def _decimal_to_json(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _json_to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def snapshot_to_jsonable(snapshot: MdmCatalogSnapshot) -> dict[str, Any]:
    return {
        "services": [
            {
                **service.__dict__,
                "price_amount": _decimal_to_json(service.price_amount),
                "price_min": _decimal_to_json(service.price_min),
                "price_max": _decimal_to_json(service.price_max),
            }
            for service in snapshot.services
        ],
        "packages": [package.__dict__ for package in snapshot.packages],
    }


def snapshot_from_jsonable(payload: dict[str, Any]) -> MdmCatalogSnapshot:
    services = [
        ServiceRecord(
            **{
                **row,
                "price_amount": _json_to_decimal(row.get("price_amount")),
                "price_min": _json_to_decimal(row.get("price_min")),
                "price_max": _json_to_decimal(row.get("price_max")),
            }
        )
        for row in payload.get("services") or []
    ]
    packages = [
        PackageRecord(**{k: v for k, v in row.items() if k != "package_detail"})
        for row in payload.get("packages") or []
    ]
    return MdmCatalogSnapshot(services=services, packages=packages)


def export_bvi_catalog_json(
    *,
    bvi_xlsx: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    source = bvi_xlsx or default_bvi_xlsx_path()
    destination = out_path or DEFAULT_BVI_JSON
    services, packages = parse_bvi_catalog(source)
    snapshot = MdmCatalogSnapshot(services=services, packages=packages)
    destination.write_text(
        json.dumps(snapshot_to_jsonable(snapshot), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination


def load_bvi_catalog_json(path: Path | None = None) -> MdmCatalogSnapshot:
    payload = json.loads((path or DEFAULT_BVI_JSON).read_text(encoding="utf-8"))
    return snapshot_from_jsonable(payload)
