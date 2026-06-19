"""Parse MDM source Excel workbooks into catalog records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

BVI_CATEGORY_ID = "harneys-bvi"
BVI_REGION = "BVI"
BVI_BU = "Harneys"
AU_CATEGORY_ID = "au-advisory"
AU_REGION = "AU"
AU_BU = "Incorp"
AU_SKU_DEPARTMENT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("SMSF", "SMSF"),
    ("CSS NEW ITEM NUMBER", "Corporate Secretarial Services"),
    ("FF NEW ITEM NUMBER", "Finance Function"),
    ("TA NEW ITEM NUMBER", "Tax and Advisory"),
    ("CSS", "Corporate Secretarial Services"),
    ("FF", "Finance Function"),
    ("TA", "Tax and Advisory"),
    ("GI", "Global Incentive"),
    ("SP", "Specialist Projects"),
)
BVI_SERVICES_SHEET = "BVI"
BVI_PACKAGES_SHEET = "Mockpackage"

GROUP_SLUG = {
    "Incorporation": "incorporation",
    "Annual maintenance": "annual_maintenance",
    "Transfer in": "transfer_in",
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
    package_semantic_for_ai: str | None
    linked_skus: list[str]
    status: str = "ACTIVE"


@dataclass
class MdmCatalogSnapshot:
    services: list[ServiceRecord]
    packages: list[PackageRecord]


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


def _fee_text(fee_raw: Any) -> str:
    s = str(fee_raw).strip() if pd.notna(fee_raw) else ""
    return "" if not s or s.lower() == "nan" else s


def parse_bvi_fee(fee_raw: Any) -> tuple[str, dict[str, Any], Decimal | None, Decimal | None, Decimal | None, str]:
    raw = _fee_text(fee_raw)
    if not raw:
        return "FIXED", {}, None, None, None, raw
    normalized = re.sub(r"\s+", " ", raw.replace("$", "").replace(",", " ")).strip()
    normalized = re.sub(r"(?<=\d) (?=\d)", "", normalized)
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", normalized)
    if m:
        return "RANGE", {}, None, Decimal(m.group(1)), Decimal(m.group(2)), raw
    m = re.match(r"^(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s+(.+)$", normalized, re.I)
    if m:
        addon = {"type": "DISBURSEMENT", "label": m.group(3).strip(), "amount": float(m.group(2))}
        return "BASE_PLUS", {"addons": [addon]}, Decimal(m.group(1)), None, None, raw
    m = re.match(r"^(\d+(?:\.\d+)?)\s*\+\s*(.+)$", normalized)
    if m and not re.search(r"^\d", m.group(2).strip()):
        return "BASE_PLUS_VARIABLE", {"variable_label": m.group(2).strip()}, Decimal(m.group(1)), None, None, raw
    if "(" in normalized and "+" in normalized:
        nums = re.findall(r"(\d+(?:\.\d+)?)", normalized)
        if nums:
            return "FIXED", {"note": raw}, Decimal(nums[0]), None, None, raw
    m = re.match(r"^(\d+(?:\.\d+)?)(?:\s+(?:per annum|one[- ]time fee|per .+))?$", normalized, re.I)
    if m:
        note = raw.lower()
        pextra: dict[str, Any] = {}
        if "per annum" in note:
            pextra["billing_note"] = "per annum"
        if "one-time" in note or "one time" in note:
            pextra["billing_note"] = "one_time"
        return "FIXED", pextra, Decimal(m.group(1)), None, None, raw
    m = re.match(r"^(\d+(?:\.\d+)?)$", normalized.replace(" ", ""))
    if m:
        return "FIXED", {}, Decimal(m.group(1)), None, None, raw
    return "FIXED", {"note": raw}, None, None, None, raw


def _infer_bvi_billing(service_group_display: str, fee_raw: str) -> tuple[str, str]:
    group = str(service_group_display or "").strip().lower()
    fee = fee_raw.lower()
    if group == "incorporation" or "one-time" in fee or "one time" in fee:
        return "ONE_TIME", "ONE_OFF"
    if group == "annual maintenance" or "per annum" in fee:
        return "ANNUALLY", "RECURRING"
    if "per annum" in fee:
        return "ANNUALLY", "RECURRING"
    return "ONE_TIME", "ONE_OFF"


def _apply_tiered_pricing(
    description: str,
    ptype: str,
    pextra: dict[str, Any],
    amount: Decimal | None,
) -> tuple[str, dict[str, Any]]:
    dl = description.lower()
    if "government fee" in dl and "50,000" in description:
        tier = "gt_50000" if "more than" in dl else "le_50000"
        return (
            "TIERED",
            {
                **pextra,
                "dimension": "share_count",
                "tier_label": tier,
                "amount": float(amount) if amount is not None else None,
            },
        )
    return ptype, pextra


def _split_package_skus(raw: Any) -> list[str]:
    text = str(raw or "")
    for sep in (";", "；", "，", ","):
        text = text.replace(sep, ";")
    return [part.strip().upper() for part in text.split(";") if part.strip()]


def au_department_team_from_sku(sku: str) -> str | None:
    normalized = sku.strip().upper()
    for prefix, department in AU_SKU_DEPARTMENT_PREFIXES:
        if normalized.startswith(prefix):
            return department
    return None


def canonical_au_package_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    if "*" in text:
        name, detail = text.split("*", 1)
        name = name.strip()
        detail = detail.strip()
        return f"{name}*{detail}" if detail else name
    if " - " in text:
        name, detail = text.split(" - ", 1)
        name = name.strip()
        detail = detail.strip()
        return f"{name}*{detail}" if detail else name
    return text


def au_package_internal_name(canonical_name: str) -> str:
    if "*" in canonical_name:
        return canonical_name.split("*", 1)[0].strip()
    return canonical_name.strip()


def load_au_package_name_map(au_xlsx: Path) -> dict[str, str]:
    try:
        aliases_df = pd.read_excel(au_xlsx, sheet_name="package").rename(
            columns={"Before": "legacy_name", "After": "canonical_name"}
        )
    except ValueError:
        return {}

    mapping: dict[str, str] = {}
    for _, row in aliases_df.iterrows():
        legacy = str(row.get("legacy_name") or "").strip()
        canonical = canonical_au_package_label(str(row.get("canonical_name") or ""))
        if legacy and canonical:
            mapping[legacy] = canonical
    return mapping


def normalize_package_sku_ref(ref: str, known_skus: set[str]) -> str | None:
    sku = ref.strip().upper()
    if sku in known_skus:
        return sku
    match = re.match(r"^(COM|AM|CSS|TRU|PW|ACC|OM)(\d+)$", sku)
    if not match:
        return None
    prefix = "COM" if match.group(1) == "OM" else match.group(1)
    candidate = f"{prefix}{int(match.group(2)):03d}"
    return candidate if candidate in known_skus else None


def default_bvi_xlsx_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "bvi-products-pricing-mock0618.xlsx"


def _read_bvi_services_df(bvi_xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(bvi_xlsx, sheet_name=BVI_SERVICES_SHEET, header=1)
    df = df.rename(
        columns={
            "Department": "department",
            "SKU code": "sku",
            "Service Name on Proposal": "service_group_display",
            "Description": "description",
            "Fee (USD$)": "fee_usd_raw",
            "Standrad pricing metrix": "pricing_matrix",
            "Comments (Sementic for AI)": "comments",
        }
    )
    df = df[df["sku"].notna()].copy()
    df["sku"] = df["sku"].astype(str).str.strip().str.upper()
    df = df[df["sku"] != "SKU CODE"].copy()
    df["service_group"] = df["service_group_display"].astype(str).map(slugify_group)
    return df


def parse_bvi_services(bvi_xlsx: Path) -> list[ServiceRecord]:
    df = _read_bvi_services_df(bvi_xlsx)
    services: list[ServiceRecord] = []
    for idx, row in df.iterrows():
        sku = str(row["sku"]).strip().upper()
        group_display = str(row["service_group_display"]).strip()
        group = str(row["service_group"]).strip()
        desc = str(row["description"]).strip()
        fee_raw = _fee_text(row["fee_usd_raw"])
        ptype, pextra, amt, pmin, pmax, _ = parse_bvi_fee(row["fee_usd_raw"])
        ptype, pextra = _apply_tiered_pricing(desc, ptype, pextra, amt)
        comments = clean_comment(row.get("comments"))
        dl = desc.lower()
        optional_kw = ("optional service", "courier", "notaris", "incumbency", "good standing")
        if comments and "optional" in comments.lower():
            stype = "OPTIONAL_ADDITIONAL"
        elif any(k in dl for k in optional_kw):
            stype = "OPTIONAL_ADDITIONAL"
        else:
            stype = "BASE_MANDATORY"
        billing_frequency, recurring = _infer_bvi_billing(group_display, fee_raw)
        services.append(
            ServiceRecord(
                sku=sku,
                category_id=BVI_CATEGORY_ID,
                region=BVI_REGION,
                bu=BVI_BU,
                department_team=str(row.get("department") or "Corporate Services").strip(),
                service_group=group,
                service_group_display=group_display,
                product_name=short_name(desc, 120),
                service_name_on_proposal=short_name(desc, 80),
                description=desc,
                scope_of_work=None,
                service_type=stype,
                billing_frequency=billing_frequency,
                recurring=recurring,
                status="ACTIVE",
                pricing_type=ptype,
                price_currency="USD",
                price_amount=amt,
                price_min=pmin,
                price_max=pmax,
                price_spec=pextra,
                fee_raw=fee_raw or None,
                footnotes=comments,
                sku_semantic_for_ai=f"BVI {group_display}: {short_name(desc, 100)}",
                external_record_id=sku,
                source_sheet=BVI_SERVICES_SHEET,
                source_row=int(idx) + 2,
            )
        )
    return services


def parse_bvi_packages(bvi_xlsx: Path, services: list[ServiceRecord]) -> list[PackageRecord]:
    known_skus = {service.sku for service in services}
    pkg_df = pd.read_excel(bvi_xlsx, sheet_name=BVI_PACKAGES_SHEET)
    packages: list[PackageRecord] = []
    for _, row in pkg_df.iterrows():
        package_id = str(row["Solution Package ID"]).strip().upper()
        package_name = str(row["Solution Package Name"]).strip()
        description = clean_comment(row.get("Solution Package Description"))
        linked_skus: list[str] = []
        for ref in _split_package_skus(row.get("SKU")):
            normalized = normalize_package_sku_ref(ref, known_skus)
            if normalized and normalized not in linked_skus:
                linked_skus.append(normalized)
        packages.append(
            PackageRecord(
                package_id=package_id,
                category_id=BVI_CATEGORY_ID,
                region=BVI_REGION,
                bu=BVI_BU,
                package_name=package_name,
                package_semantic_for_ai=description or package_name,
                linked_skus=linked_skus,
            )
        )
    return packages


def parse_bvi_catalog(bvi_xlsx: Path) -> tuple[list[ServiceRecord], list[PackageRecord]]:
    services = parse_bvi_services(bvi_xlsx)
    packages = parse_bvi_packages(bvi_xlsx, services)
    return services, packages


def parse_au_advisory_catalog(
    au_xlsx: Path,
) -> tuple[list[ServiceRecord], list[PackageRecord]]:
    au_df = pd.read_excel(au_xlsx, sheet_name="All products")
    adv = au_df[~au_df["SKU"].astype(str).str.match(r"^ADT", na=False)].copy()
    package_name_map = load_au_package_name_map(au_xlsx)

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
                category_id=AU_CATEGORY_ID,
                region=AU_REGION,
                bu=AU_BU,
                department_team=au_department_team_from_sku(sku),
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
            if part in package_name_map:
                canonical_name = package_name_map[part]
            else:
                canonical_name = canonical_au_package_label(part)
            internal_name = au_package_internal_name(canonical_name)
            pkg_id = "PKG-AU-" + hashlib.md5(internal_name.encode()).hexdigest()[:8].upper()
            if pkg_id not in pkg_map:
                pkg_map[pkg_id] = PackageRecord(
                    package_id=pkg_id,
                    category_id=AU_CATEGORY_ID,
                    region=AU_REGION,
                    bu=AU_BU,
                    package_name=canonical_name,
                    package_semantic_for_ai=canonical_name,
                    linked_skus=[],
                )
            if sku not in pkg_map[pkg_id].linked_skus:
                pkg_map[pkg_id].linked_skus.append(sku)

    return services, list(pkg_map.values())


def load_mdm_snapshot(
    *,
    bvi_xlsx: Path,
    au_xlsx: Path,
) -> MdmCatalogSnapshot:
    bvi_services, bvi_packages = parse_bvi_catalog(bvi_xlsx)
    au_services, au_packages = parse_au_advisory_catalog(au_xlsx)
    return MdmCatalogSnapshot(
        services=bvi_services + au_services,
        packages=bvi_packages + au_packages,
    )
