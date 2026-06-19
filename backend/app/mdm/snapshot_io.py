"""Load the BVI MDM catalog snapshot used by the Alembic seed migration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

DEFAULT_BVI_JSON = Path(__file__).resolve().parent / "data" / "bvi_catalog.json"


@dataclass
class ServiceRecord:
    sku: str
    region: str
    bu: str
    department_team: str | None
    service_group: str | None
    service_group_display: str | None
    product_name: str
    service_name_on_proposal: str
    description: str | None
    scope_of_work: str | None
    service_type: str
    billing_frequency: str
    recurring: str
    status: str
    pricing_type: str
    price_currency: str
    price_amount: Decimal | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_spec: dict[str, Any]
    fee_raw: str | None
    footnotes: str | None
    sku_semantic_for_ai: str | None
    external_record_id: str | None
    source_sheet: str | None
    source_row: int | None
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass
class PackageRecord:
    package_id: str
    region: str
    bu: str
    package_name: str
    package_semantic_for_ai: str | None
    linked_skus: list[str]
    status: str = "ACTIVE"


@dataclass
class MdmCatalogSnapshot:
    services: list[ServiceRecord]
    packages: list[PackageRecord]


def _json_to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


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


def load_bvi_catalog_json(path: Path | None = None) -> MdmCatalogSnapshot:
    payload = json.loads((path or DEFAULT_BVI_JSON).read_text(encoding="utf-8"))
    return snapshot_from_jsonable(payload)
