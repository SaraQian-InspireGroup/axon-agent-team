"""Fee row source/display model — materialize, resolve, and effective pricing."""

from __future__ import annotations

import copy
import re
from typing import Any

from app.proposal.fee_table import format_money, row_frequency_columns, row_total_annualized
from app.proposal.footnotes import normalize_footnote
from app.proposal.pricing_rules import coerce_price_amount, fee_table_amount_display, normalize_pricing_type

_STANDARD_OFFER_RE = re.compile(r"\s*\((?:standard offer|standard fee|pricing)[^)]+\)\s*$", re.I)
_AMOUNT_PARSE_RE = re.compile(r"[\d,]+\.?\d*")


def _clean_service_name(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    cleaned = _STANDARD_OFFER_RE.sub("", raw).strip()
    return cleaned or raw


def _normalize_department(value: Any) -> str:
    dept = str(value or "").strip()
    if not dept or dept.lower() == "nan":
        return "Services"
    return dept


def parse_amount_display(text: str | None) -> float | None:
    if not text:
        return None
    match = _AMOUNT_PARSE_RE.search(str(text).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def build_mdm_source(
    service: dict[str, Any],
    *,
    package_id: str | None = None,
    jurisdiction: str | None = None,
    bu: str | None = None,
) -> dict[str, Any]:
    sku = str(service["sku"])
    source: dict[str, Any] = {
        "type": "mdm_service",
        "sku": sku,
        "service_name": _clean_service_name(service.get("service_name")) or sku,
        "description": str(service.get("description") or "").strip() or None,
        "scope_of_work": str(service.get("scope_of_work") or "").strip() or None,
        "department_team": _normalize_department(service.get("department_team")),
        "billing_frequency": str(service.get("billing_frequency") or "ONE_TIME").strip(),
        "recurring": str(service.get("recurring") or "ONE_OFF").strip(),
        "status": "ACTIVE",
        "pricing_type": normalize_pricing_type(service.get("pricing_type")),
        "price_currency": str(service.get("price_currency") or "").strip() or None,
        "price_amount": coerce_price_amount(service.get("price_amount")),
        "fee_raw": str(service.get("fee_raw") or "").strip() or None,
        "footnotes": normalize_footnote(service.get("footnotes")),
    }
    if package_id:
        source["package_id"] = package_id
    if jurisdiction:
        source["jurisdiction"] = jurisdiction
    if bu:
        source["bu"] = bu
    semantic = str(service.get("sku_semantic_for_ai") or "").strip()
    if semantic:
        source["sku_semantic_for_ai"] = semantic
    return source


def build_custom_source(*, sku: str) -> dict[str, Any]:
    return {"type": "custom_service", "sku": sku}


def _price_object_from_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": coerce_price_amount(source.get("price_amount")),
        "fee_raw": source.get("fee_raw"),
        "currency": source.get("price_currency") or "",
        "frequency": source.get("billing_frequency") or "ONE_TIME",
        "recurring": source.get("recurring") or "ONE_OFF",
        "pricing_type": normalize_pricing_type(source.get("pricing_type")),
    }


def _preview_primary(source: dict[str, Any], layout: dict[str, Any]) -> str:
    from app.proposal.fee_table import service_column_flags

    columns = service_column_flags(layout)
    service_name = str(source.get("service_name") or source.get("sku") or "").strip()
    description = str(source.get("description") or "").strip()
    sku = str(source.get("sku") or "").strip()

    if columns.get("service_name") and service_name:
        return service_name
    if columns.get("description") and description:
        return description
    return sku or service_name or description


def _format_frequency_column_display(amount: float | None, currency: str) -> str:
    if amount is None:
        return ""
    return format_money(amount, currency, include_currency=bool(currency)).strip()


def resolve_fee_row(source: dict[str, Any], *, layout: dict[str, Any]) -> dict[str, Any]:
    from app.proposal.fee_table import service_column_flags

    columns = service_column_flags(layout)
    price = _price_object_from_source(source)
    currency = str(price.get("currency") or "")
    table_style = str(layout.get("table_style") or "simple").strip().lower()

    display: dict[str, Any] = {
        "preview_primary": _preview_primary(source, layout),
    }

    footnotes = normalize_footnote(source.get("footnotes"))
    if footnotes:
        display["footnotes_display"] = footnotes

    if columns.get("scope_of_work"):
        sow = str(source.get("scope_of_work") or "").strip()
        if sow:
            display["scope_of_work_display"] = sow

    if table_style == "frequency_columns":
        amount = price.get("amount")
        freq_cols = row_frequency_columns(
            {
                "amount": amount,
                "billing_frequency": price.get("frequency"),
            }
        )
        display["frequency_columns_display"] = {
            key: _format_frequency_column_display(freq_cols.get(key), currency)
            for key in ("monthly", "quarterly", "annual", "once_off")
        }
        total = row_total_annualized(freq_cols) if amount is not None else None
        display["total_display"] = (
            format_money(total, currency, include_currency=bool(currency)).strip()
            if total is not None
            else ""
        )
        fee_raw = fee_table_amount_display(price, format_money=format_money)
        if fee_raw and normalize_pricing_type(price.get("pricing_type")) != "FIXED":
            active = str(price.get("frequency") or "ONE_TIME").upper()
            col_map = {
                "MONTHLY": "monthly",
                "QUARTERLY": "quarterly",
                "ANNUALLY": "annual",
            }
            active_key = col_map.get(active, "once_off")
            display["frequency_columns_display"][active_key] = fee_raw
    else:
        amount_text = fee_table_amount_display(price, format_money=format_money)
        if amount_text:
            display["amount_display"] = amount_text

    return display


def resolve_fee_row_display(row: dict[str, Any], *, layout: dict[str, Any]) -> dict[str, Any]:
    source = row.get("source")
    if not isinstance(source, dict):
        raise ValueError("fee_row.source must be an object")
    display = copy.deepcopy(row.get("display") or {})
    if str(source.get("type") or "") == "custom_service":
        return _normalize_custom_display(display, layout=layout)
    if display:
        return _apply_display_overrides(source, display, layout=layout)
    return resolve_fee_row(source, layout=layout)


def _apply_display_overrides(
    source: dict[str, Any],
    display: dict[str, Any],
    *,
    layout: dict[str, Any],
) -> dict[str, Any]:
    """Recompute derived display fields after explicit display edits."""
    table_style = str(layout.get("table_style") or "simple").strip().lower()
    price = _price_object_from_source(source)
    currency = str(price.get("currency") or "")

    if "amount_display" in display and table_style != "frequency_columns":
        parsed = parse_amount_display(str(display.get("amount_display") or ""))
        if parsed is not None:
            price = {**price, "amount": parsed}
            display["amount_display"] = fee_table_amount_display(price, format_money=format_money) or display["amount_display"]

    if table_style == "frequency_columns":
        amount = price.get("amount")
        explicit_freq = isinstance(display.get("frequency_columns_display"), dict)
        if "amount_display" in display:
            parsed = parse_amount_display(str(display.get("amount_display") or ""))
            if parsed is not None:
                amount = parsed
                price = {**price, "amount": parsed}
        if amount is not None and (not explicit_freq):
            freq_cols = row_frequency_columns(
                {"amount": amount, "billing_frequency": price.get("frequency")}
            )
            display["frequency_columns_display"] = {
                key: _format_frequency_column_display(freq_cols.get(key), currency)
                for key in ("monthly", "quarterly", "annual", "once_off")
            }
            total = row_total_annualized(freq_cols)
            display["total_display"] = format_money(total, currency, include_currency=bool(currency)).strip()
            fee_raw = fee_table_amount_display(price, format_money=format_money)
            if fee_raw and normalize_pricing_type(price.get("pricing_type")) != "FIXED":
                active = str(price.get("frequency") or "ONE_TIME").upper()
                col_map = {
                    "MONTHLY": "monthly",
                    "QUARTERLY": "quarterly",
                    "ANNUALLY": "annual",
                }
                active_key = col_map.get(active, "once_off")
                display["frequency_columns_display"][active_key] = fee_raw
        elif explicit_freq and "total_display" not in display and amount is not None:
            freq_cols = row_frequency_columns(
                {"amount": amount, "billing_frequency": price.get("frequency")}
            )
            total = row_total_annualized(freq_cols)
            display["total_display"] = format_money(total, currency, include_currency=bool(currency)).strip()

    if "preview_primary" not in display or not str(display.get("preview_primary") or "").strip():
        display["preview_primary"] = _preview_primary(source, layout)

    return display


def _normalize_custom_display(display: dict[str, Any], *, layout: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(display)
    preview = str(normalized.get("preview_primary") or "").strip()
    if not preview:
        raise ValueError("custom fee_row.display.preview_primary is required")
    amount_text = str(normalized.get("amount_display") or "").strip()
    table_style = str(layout.get("table_style") or "simple").strip().lower()
    if table_style == "frequency_columns":
        if "frequency_columns_display" not in normalized and amount_text:
            parsed = parse_amount_display(amount_text)
            currency = ""
            if amount_text.upper().startswith("AUD"):
                currency = "AUD"
            elif amount_text.upper().startswith("USD"):
                currency = "USD"
            cols = row_frequency_columns({"amount": parsed, "billing_frequency": "ONE_TIME"})
            normalized["frequency_columns_display"] = {
                key: _format_frequency_column_display(cols.get(key), currency)
                for key in ("monthly", "quarterly", "annual", "once_off")
            }
            if parsed is not None:
                normalized["total_display"] = format_money(parsed, currency, include_currency=bool(currency)).strip()
    elif amount_text:
        normalized["amount_display"] = amount_text
    return normalized


def materialize_mdm_fee_row(
    service: dict[str, Any],
    *,
    package_id: str | None,
    layout: dict[str, Any],
    jurisdiction: str | None = None,
    bu: str | None = None,
) -> dict[str, Any]:
    source = build_mdm_source(
        service,
        package_id=package_id,
        jurisdiction=jurisdiction,
        bu=bu,
    )
    display = resolve_fee_row(source, layout=layout)
    return {
        "id": f"fee_{source['sku']}",
        "kind": "fee_row",
        "source": source,
        "display": display,
    }


def materialize_custom_fee_row(
    *,
    sku: str,
    display: dict[str, Any],
    layout: dict[str, Any],
) -> dict[str, Any]:
    source = build_custom_source(sku=sku)
    normalized_display = _normalize_custom_display(display, layout=layout)
    return {
        "id": f"fee_{sku}",
        "kind": "fee_row",
        "source": source,
        "display": normalized_display,
    }


def row_sku(row: dict[str, Any]) -> str:
    source = row.get("source")
    if isinstance(source, dict) and source.get("sku"):
        return str(source["sku"]).strip()
    row_id = str(row.get("id") or "").strip()
    if row_id.startswith("fee_"):
        return row_id.removeprefix("fee_")
    return row_id


def row_department(row: dict[str, Any]) -> str:
    source = row.get("source")
    if isinstance(source, dict):
        return _normalize_department(source.get("department_team"))
    return "Services"


def row_footnote_text(row: dict[str, Any]) -> str | None:
    display = row.get("display")
    if isinstance(display, dict):
        text = normalize_footnote(display.get("footnotes_display"))
        if text:
            return text
    source = row.get("source")
    if isinstance(source, dict):
        return normalize_footnote(source.get("footnotes"))
    return None


def effective_pricing(row: dict[str, Any]) -> dict[str, Any]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    display = row.get("display") if isinstance(row.get("display"), dict) else {}
    source_type = str(source.get("type") or "")

    if source_type == "custom_service":
        amount = parse_amount_display(str(display.get("amount_display") or ""))
        if amount is None and isinstance(display.get("frequency_columns_display"), dict):
            for key in ("once_off", "annual", "quarterly", "monthly"):
                parsed = parse_amount_display(str(display["frequency_columns_display"].get(key) or ""))
                if parsed is not None:
                    amount = parsed
                    break
        billing_frequency = "ONE_TIME"
        currency = ""
        amount_text = str(display.get("amount_display") or display.get("total_display") or "")
        if "AUD" in amount_text.upper():
            currency = "AUD"
        elif "USD" in amount_text.upper():
            currency = "USD"
        converted = {
            "amount": amount,
            "billing_frequency": billing_frequency,
            "currency": currency,
            "pricing_type": "FIXED",
        }
        converted["frequency_columns"] = row_frequency_columns(converted)
        return converted

    price = _price_object_from_source(source)
    active = str(price.get("frequency") or "ONE_TIME").upper()
    col_map = {
        "MONTHLY": "monthly",
        "QUARTERLY": "quarterly",
        "ANNUALLY": "annual",
        "ONE_TIME": "once_off",
    }
    active_key = col_map.get(active, "once_off")
    if isinstance(display.get("frequency_columns_display"), dict):
        parsed = parse_amount_display(str(display["frequency_columns_display"].get(active_key) or ""))
        if parsed is not None:
            price["amount"] = parsed
    if "amount_display" in display and not isinstance(display.get("frequency_columns_display"), dict):
        parsed = parse_amount_display(str(display.get("amount_display") or ""))
        if parsed is not None:
            price["amount"] = parsed

    converted = {
        "amount": price.get("amount"),
        "billing_frequency": price.get("frequency") or "ONE_TIME",
        "currency": price.get("currency") or "",
        "pricing_type": price.get("pricing_type"),
        "amount_display": display.get("amount_display") or display.get("total_display"),
    }
    converted["frequency_columns"] = row_frequency_columns(converted)
    return converted


def render_row_dto(row: dict[str, Any]) -> dict[str, Any]:
    """Minimal row payload for preview render and footnote collection."""
    display = row.get("display") if isinstance(row.get("display"), dict) else {}
    pricing = effective_pricing(row)
    dto: dict[str, Any] = {
        "sku": row_sku(row),
        "department_team": row_department(row),
        "footnotes": row_footnote_text(row),
        "display": copy.deepcopy(display),
        "preview_primary": display.get("preview_primary"),
        "amount_display": display.get("amount_display") or display.get("total_display"),
        "amount": pricing.get("amount"),
        "currency": pricing.get("currency"),
        "billing_frequency": pricing.get("billing_frequency"),
        "pricing_type": pricing.get("pricing_type"),
        "frequency_columns": pricing.get("frequency_columns"),
    }
    if isinstance(display.get("frequency_columns_display"), dict):
        dto["frequency_columns_display"] = copy.deepcopy(display["frequency_columns_display"])
    if display.get("scope_of_work_display"):
        dto["scope_of_work_display"] = display.get("scope_of_work_display")
    return dto


def iter_fee_rows(draft: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Yield (section, table, row) for each fee_row in the draft."""
    document = draft.get("document") or {}
    sections = document.get("sections") if isinstance(document, dict) else []
    if not isinstance(sections, list):
        return []
    found: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for section in sections:
        if not isinstance(section, dict) or section.get("kind") != "fee_section":
            continue
        for table in section.get("tables") or []:
            if not isinstance(table, dict):
                continue
            for row in table.get("rows") or []:
                if isinstance(row, dict) and row.get("kind") == "fee_row":
                    found.append((section, table, row))
    return found


def remove_fee_rows_by_sku(draft: dict[str, Any], skus: list[str]) -> dict[str, Any]:
    targets = {str(sku).strip() for sku in skus if str(sku).strip()}
    if not targets:
        raise ValueError("skus are required")
    updated = copy.deepcopy(draft)
    removed = 0
    for section in (updated.get("document") or {}).get("sections") or []:
        if not isinstance(section, dict) or section.get("kind") != "fee_section":
            continue
        for table in section.get("tables") or []:
            if not isinstance(table, dict):
                continue
            rows = table.get("rows") or []
            kept = [row for row in rows if isinstance(row, dict) and row_sku(row) not in targets]
            removed += len(rows) - len(kept)
            table["rows"] = kept
    if removed == 0:
        raise ValueError(f"No fee rows matched skus: {', '.join(sorted(targets))}")
    return updated

def validate_fee_row_patches(patch: list[dict[str, Any]]) -> None:
    from app.proposal.draft import DraftPatchError

    for op in patch:
        if not isinstance(op, dict):
            continue
        path = str(op.get("path") or "")
        if "/source" in path and "/rows/" in path:
            raise DraftPatchError("fee_row.source is immutable; patch display fields instead.")
