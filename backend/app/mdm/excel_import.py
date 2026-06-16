"""Parse MDM source Excel workbooks into catalog records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

GROUP_SLUG = {
    "Incorporation": "incorporation",
    "Annual maintenance": "annual_maintenance",
    "Transfer in ": "transfer_in",
    "FAR": "far",
}

@dataclass
class ServiceRecord:
    sku: str
    category_id: str
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
    category_id: str
    region: str
    bu: str
    package_name: str
    package_detail: str | None
    package_semantic_for_ai: str | None
    linked_skus: list[str]
    status: str = "ACTIVE"


@dataclass
class PackageNameAlias:
    legacy_name: str
    canonical_name: str
    region: str = "AU"


@dataclass
class MdmCatalogSnapshot:
    services: list[ServiceRecord]
    packages: list[PackageRecord]
    package_aliases: list[PackageNameAlias]


def slugify_group(name: str) -> str:
    if name in GROUP_SLUG:
        return GROUP_SLUG[name]
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(name).strip()).strip("_").lower()
    return slug[:48] or "other"


def short_name(desc: str, max_len: int = 80) -> str:
    d = re.sub(r"\s+", " ", str(desc).strip())
    return d if len(d) <= max_len else d[: max_len - 3] + "..."


def clean_comment(value: Any) -> str | None:
    s = str(value or "").strip()
    return None if s.lower() in ("nan", "none", "") else s


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if value == "":
        return None
    return Decimal(str(value))


def parse_bvi_fee(fee_raw: Any) -> tuple[str, dict[str, Any], Decimal | None, Decimal | None, Decimal | None, str]:
    s = str(fee_raw).strip() if pd.notna(fee_raw) else ""
    if not s or s.lower() == "nan":
        return "FIXED", {}, None, None, None, s
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s.replace("$", ""))
    if m:
        return "RANGE", {}, Decimal(m.group(1)), Decimal(m.group(2)), None, s
    m = re.match(r"^(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s+(.+)$", s, re.I)
    if m:
        addon = {"type": "DISBURSEMENT", "label": m.group(3).strip(), "amount": float(m.group(2))}
        return "BASE_PLUS", {"addons": [addon]}, Decimal(m.group(1)), None, None, s
    m = re.match(r"^(\d+(?:\.\d+)?)\s*\+\s*(.+)$", s)
    if m and not re.search(r"^\d", m.group(2).strip()):
        return "BASE_PLUS_VARIABLE", {"variable_label": m.group(2).strip()}, Decimal(m.group(1)), None, None, s
    if "(" in s and "+" in s:
        nums = re.findall(r"(\d+(?:\.\d+)?)", s)
        if nums:
            return "FIXED", {"note": s}, Decimal(nums[0]), None, None, s
    m = re.match(r"^(\d+(?:\.\d+)?)$", s.replace(",", ""))
    if m:
        return "FIXED", {}, Decimal(m.group(1)), None, None, s
    return "FIXED", {"note": s}, None, None, None, s


def parse_bvi_catalog(bvi_xlsx: Path) -> tuple[list[ServiceRecord], list[PackageRecord]]:
    df = pd.read_excel(bvi_xlsx, sheet_name="BVI", header=1)
    df = df.rename(
        columns={
            "Department": "department",
            "Service": "service_group_display",
            "Description": "description",
            "Fee (USD$)": "fee_usd_raw",
            "Comments": "comments",
        }
    )
    df = df[df["description"].notna() & (df["description"] != "Description")].copy()
    df["service_group"] = df["service_group_display"].map(slugify_group)

    services: list[ServiceRecord] = []
    counters: dict[str, int] = {}
    for idx, row in df.iterrows():
        group = row["service_group"]
        counters[group] = counters.get(group, 0) + 1
        sku = f"BVI-{group}-{counters[group]:03d}"
        ptype, pextra, amt, pmin, pmax, raw_fee = parse_bvi_fee(row["fee_usd_raw"])
        desc = str(row["description"]).strip()
        dl = desc.lower()
        optional_kw = ("optional service", "courier", "notaris", "incumbency", "good standing")
        stype = "OPTIONAL_ADDITIONAL" if any(k in dl for k in optional_kw) else "BASE_MANDATORY"
        if "government fee" in dl and "50,000" in desc:
            tier = "gt_50000" if "more than" in dl else "le_50000"
            ptype = "TIERED"
            pextra = {"dimension": "share_count", "tier_label": tier, "amount": float(amt) if amt else None}
        services.append(
            ServiceRecord(
                sku=sku,
                category_id="harneys-bvi",
                region="BVI",
                bu="Harneys",
                department_team=str(row.get("department") or "Corporate Services").strip(),
                service_group=group,
                service_group_display=str(row["service_group_display"]).strip(),
                product_name=short_name(desc, 120),
                service_name_on_proposal=short_name(desc, 80),
                description=desc,
                scope_of_work=None,
                service_type=stype,
                billing_frequency="ONE_TIME" if group == "incorporation" else "ANNUALLY",
                recurring="ONE_OFF" if group == "incorporation" else "RECURRING",
                status="ACTIVE",
                pricing_type=ptype,
                price_currency="USD",
                price_amount=amt,
                price_min=pmin,
                price_max=pmax,
                price_spec=pextra,
                fee_raw=raw_fee or None,
                footnotes=clean_comment(row.get("comments")),
                sku_semantic_for_ai=f"BVI {row['service_group_display']}: {short_name(desc, 100)}",
                external_record_id=None,
                source_sheet="BVI",
                source_row=int(idx) + 2,
            )
        )

    inc_skus = [s.sku for s in services if s.service_group == "incorporation"][:6]
    ann_skus = [s.sku for s in services if s.service_group == "annual_maintenance"][:6]
    packages = [
        PackageRecord(
            package_id="PKG-BVI-INCORP-STD",
            category_id="harneys-bvi",
            region="BVI",
            bu="Harneys",
            package_name="BVI Standard Incorporation Package",
            package_detail=None,
            package_semantic_for_ai="Typical BVI new incorporation bundle from MDM",
            linked_skus=inc_skus,
        ),
        PackageRecord(
            package_id="PKG-BVI-ANN-STD",
            category_id="harneys-bvi",
            region="BVI",
            bu="Harneys",
            package_name="BVI Standard Annual Maintenance Package",
            package_detail=None,
            package_semantic_for_ai="Typical BVI annual compliance bundle from MDM",
            linked_skus=ann_skus,
        ),
    ]
    return services, packages


def parse_au_advisory_catalog(
    au_xlsx: Path,
) -> tuple[list[ServiceRecord], list[PackageRecord], list[PackageNameAlias]]:
    au_df = pd.read_excel(au_xlsx, sheet_name="All products")
    adv = au_df[~au_df["SKU"].astype(str).str.match(r"^ADT", na=False)].copy()

    def norm_billing(value: Any) -> str:
        s = str(value or "").strip().lower()
        return {
            "annually": "ANNUALLY",
            "annual": "ANNUALLY",
            "monthly": "MONTHLY",
            "quarterly": "QUARTERLY",
        }.get(s, "ONE_TIME")

    services: list[ServiceRecord] = []
    for idx, row in adv.iterrows():
        sku = str(row["SKU"]).strip()
        matrix = str(row.get("Standard pricing matrix for proposal", "") or "").strip()
        ptype = "MATRIX_REF" if matrix and matrix.lower() != "nan" else "FIXED"
        pextra: dict[str, Any] = (
            {"matrix_label": matrix, "matrix_for_proposal": matrix} if ptype == "MATRIX_REF" else {}
        )
        price = row["Price AUD"]
        scope = str(row.get("Scope of work", "") or "").strip() or None
        services.append(
            ServiceRecord(
                sku=sku,
                category_id="au-services",
                region="AU",
                bu="Tax and Advisory",
                department_team=sku[:2] if len(sku) >= 2 else None,
                service_group=None,
                service_group_display=None,
                product_name=str(row.get("Name", "") or "").strip(),
                service_name_on_proposal=str(
                    row.get("Service name on proposal", "") or row.get("Name", "")
                ).strip(),
                description=str(row.get("Product description", "") or "").strip() or None,
                scope_of_work=scope,
                service_type="BASE_MANDATORY",
                billing_frequency=norm_billing(row.get("Billing frequency")),
                recurring="RECURRING"
                if str(row.get("Recurring", "")).strip().lower() == "recurring"
                else "ONE_OFF",
                status="ACTIVE",
                pricing_type=ptype,
                price_currency="AUD",
                price_amount=_to_decimal(price) if pd.notna(price) and price != 0 else None,
                price_min=None,
                price_max=None,
                price_spec=pextra,
                fee_raw=None,
                footnotes=None,
                sku_semantic_for_ai=str(row.get("Name", "") or "").strip(),
                external_record_id=str(row.get("Record ID", "")) or None,
                source_sheet="All products",
                source_row=int(idx) + 2,
            )
        )

    pkg_map: dict[str, PackageRecord] = {}
    for _, row in adv.iterrows():
        sku = str(row["SKU"]).strip()
        sp = str(row.get("Solution Package", "") or "").strip()
        if not sp or sp.lower() == "nan":
            continue
        for part in sp.split(";"):
            part = part.strip()
            if not part:
                continue
            if "*" in part:
                name, detail = part.split("*", 1)
                pkg_name, pkg_detail = name.strip(), detail.strip()
            else:
                pkg_name, pkg_detail = part, ""
            pkg_id = "PKG-AU-" + hashlib.md5(pkg_name.encode()).hexdigest()[:8].upper()
            if pkg_id not in pkg_map:
                pkg_map[pkg_id] = PackageRecord(
                    package_id=pkg_id,
                    category_id="au-services",
                    region="AU",
                    bu="Tax and Advisory",
                    package_name=pkg_name,
                    package_detail=pkg_detail or None,
                    package_semantic_for_ai=pkg_detail or pkg_name,
                    linked_skus=[],
                )
            if sku not in pkg_map[pkg_id].linked_skus:
                pkg_map[pkg_id].linked_skus.append(sku)

    aliases_df = pd.read_excel(au_xlsx, sheet_name="package").rename(
        columns={"Before": "legacy_name", "After": "canonical_name"}
    )
    aliases = [
        PackageNameAlias(
            legacy_name=str(r["legacy_name"]).strip(),
            canonical_name=str(r["canonical_name"]).strip(),
        )
        for _, r in aliases_df.iterrows()
        if str(r.get("legacy_name", "")).strip()
    ]

    return services, list(pkg_map.values()), aliases


def load_mdm_snapshot(
    *,
    bvi_xlsx: Path,
    au_xlsx: Path,
) -> MdmCatalogSnapshot:
    bvi_services, bvi_packages = parse_bvi_catalog(bvi_xlsx)
    au_services, au_packages, au_aliases = parse_au_advisory_catalog(au_xlsx)
    return MdmCatalogSnapshot(
        services=bvi_services + au_services,
        packages=bvi_packages + au_packages,
        package_aliases=au_aliases,
    )
