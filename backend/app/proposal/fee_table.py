"""Fee table rendering helpers — frequency columns, grouping totals, payment options."""

from __future__ import annotations

import html
import re
from typing import Any


def escape_html(text: str) -> str:
    return html.escape(str(text).strip(), quote=True)


def escape_table_cell(text: str) -> str:
    """Legacy markdown cell helper — pipes must be removed, not escaped, in GFM tables."""
    cleaned = re.sub(r"\s+", " ", str(text).strip())
    return cleaned.replace("|", "/")


def format_scope_html(scope: str) -> str:
    """Render scope_of_work inside a table cell (paragraphs and bullet lists)."""
    raw = str(scope).strip()
    if not raw:
        return ""

    lines = [ln.strip() for ln in re.split(r"\r?\n", raw) if ln.strip()]
    if not lines:
        return ""

    bullet_prefix = re.compile(r"^[-*•]\s+")
    bullets = [bullet_prefix.sub("", ln) for ln in lines if bullet_prefix.match(ln)]
    prose = [ln for ln in lines if not bullet_prefix.match(ln)]

    if not bullets and len(lines) == 1:
        single = lines[0]
        if ":" in single and any(token in single.lower() for token in ("including", "covering", "such as")):
            head, tail = single.split(":", 1)
            segments = [seg.strip() for seg in re.split(r";|\n", tail) if seg.strip()]
            if len(segments) > 1:
                items = "".join(f"<li>{escape_html(seg)}</li>" for seg in segments)
                return f"<p><strong>{escape_html(head.strip())}:</strong></p><ul>{items}</ul>"

    parts: list[str] = []
    if prose:
        parts.append(f"<p>{escape_html(' '.join(prose))}</p>")
    if bullets:
        items = "".join(f"<li>{escape_html(item)}</li>" for item in bullets)
        parts.append(f"<ul>{items}</ul>")
    return "".join(parts)


def build_service_cell_html(
    index: int,
    sub: int,
    label: str,
    *,
    scope: str | None = None,
    note: str | None = None,
) -> str:
    parts = [f"<strong>{escape_html(f'{index}.{sub} {label}')}</strong>"]
    if scope:
        scope_html = format_scope_html(scope)
        if scope_html:
            parts.append(scope_html)
    if note:
        parts.append(f"<p><em>{escape_html(note)}</em></p>")
    return "".join(parts)


def row_frequency_columns(row: dict[str, Any]) -> dict[str, float | None]:
    amount = row.get("amount")
    if amount is None:
        return {"monthly": None, "quarterly": None, "annual": None, "once_off": None}
    freq = str(row.get("billing_frequency") or "ONE_TIME").upper()
    value = float(amount)
    cols = {"monthly": None, "quarterly": None, "annual": None, "once_off": None}
    if freq == "MONTHLY":
        cols["monthly"] = value
    elif freq == "QUARTERLY":
        cols["quarterly"] = value
    elif freq == "ANNUALLY":
        cols["annual"] = value
    else:
        cols["once_off"] = value
    return cols


_LABEL_COL_WIDTH = "33.333%"
_AMOUNT_COL_WIDTH = "13.333%"
_TABLE_STYLE = "width:100%;table-layout:fixed;border-collapse:collapse"


def format_money(amount: float | None, currency: str = "", *, include_currency: bool = True) -> str:
    if amount is None:
        return ""
    prefix = f"{currency} " if include_currency and currency else ""
    return f"{prefix}${amount:,.2f}"


def row_total_amount(row: dict[str, Any]) -> float | None:
    cols = row.get("frequency_columns") or row_frequency_columns(row)
    values = [cols.get("monthly"), cols.get("quarterly"), cols.get("annual"), cols.get("once_off")]
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return sum(present)


def sum_group_columns(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals = {"monthly": 0.0, "quarterly": 0.0, "annual": 0.0, "once_off": 0.0}
    for row in rows:
        cols = row.get("frequency_columns") or row_frequency_columns(row)
        for key in totals:
            value = cols.get(key)
            if value is not None:
                totals[key] += float(value)
    return totals


def row_total_annualized(cols: dict[str, float | None]) -> float:
    monthly = float(cols.get("monthly") or 0)
    quarterly = float(cols.get("quarterly") or 0)
    annual = float(cols.get("annual") or 0)
    once_off = float(cols.get("once_off") or 0)
    return monthly * 12 + quarterly * 4 + annual + once_off


def recurring_annualized(cols: dict[str, float | None]) -> float:
    monthly = float(cols.get("monthly") or 0)
    quarterly = float(cols.get("quarterly") or 0)
    annual = float(cols.get("annual") or 0)
    return monthly * 12 + quarterly * 4 + annual


def payment_summary_footer(rows: list[dict[str, Any]]) -> dict[str, float]:
    once_off = sum(float(row.get("once_off") or 0) for row in rows)
    recurring = sum(recurring_annualized(row) for row in rows)
    return {"once_off_total": once_off, "recurring_annualized_total": recurring}


def _amount_cell(
    amount: float | None,
    currency: str,
    *,
    include_currency: bool = False,
    compact_layout: bool = False,
) -> str:
    text = format_money(amount, currency, include_currency=include_currency)
    if compact_layout:
        return (
            f"<td width=\"{_AMOUNT_COL_WIDTH}\" class=\"proposal-fee-amount\" "
            f"style=\"width:{_AMOUNT_COL_WIDTH}\">"
            f"{escape_html(text) if text else '&nbsp;'}</td>"
        )
    return f"<td class=\"proposal-fee-amount\">{escape_html(text) if text else '&nbsp;'}</td>"


def _fee_table_colgroup() -> str:
    amount_col = (
        f'<col width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-col-amount" />'
    )
    return (
        "<colgroup>"
        f'<col width="{_LABEL_COL_WIDTH}" style="width:{_LABEL_COL_WIDTH}" '
        f'class="proposal-fee-col-label" />'
        f"{amount_col * 5}"
        "</colgroup>"
    )


def _fee_table_head(label: str) -> str:
    return (
        "<thead><tr>"
        f'<th width="{_LABEL_COL_WIDTH}" style="width:{_LABEL_COL_WIDTH}">{label}</th>'
        f'<th width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-amount-head">Monthly</th>'
        f'<th width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-amount-head">Quarterly</th>'
        f'<th width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-amount-head">Annual</th>'
        f'<th width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-amount-head">Once-Off</th>'
        f'<th width="{_AMOUNT_COL_WIDTH}" style="width:{_AMOUNT_COL_WIDTH}" '
        f'class="proposal-fee-amount-head">Total</th>'
        "</tr></thead><tbody>"
    )


def _payment_table_head() -> str:
    return (
        "<thead><tr>"
        "<th>Option</th>"
        "<th>Monthly Fees</th>"
        "<th>Quarterly Fees</th>"
        "<th>Annual Fees</th>"
        "<th>Once-Off Fees</th>"
        "<th>Total Fees (Annualised)</th>"
        "</tr></thead><tbody>"
    )


def render_frequency_table(
    groups: list[dict[str, Any]],
    *,
    currency: str = "",
    include_scope: bool = False,
) -> str:
    parts: list[str] = []
    for index, group in enumerate(groups, 1):
        title = group.get("display_name") or group.get("group_id") or f"{index}. Services"
        heading = f"### {index}. {title}" if not str(title).startswith(f"{index}.") else f"### {title}"
        parts.append(heading)
        parts.append("")
        parts.append(
            f"<table class=\"proposal-fee-table proposal-fee-table-frequency\" style=\"{_TABLE_STYLE}\">"
        )
        parts.append(_fee_table_colgroup())
        parts.append(_fee_table_head("Service"))
        sub = 1
        for row in group.get("rows") or []:
            cols = row.get("frequency_columns") or row_frequency_columns(row)
            total = row_total_amount({**row, "frequency_columns": cols})
            label = str(row.get("label") or row.get("sku"))
            service_html = build_service_cell_html(
                index,
                sub,
                label,
                scope=str(row["scope_of_work"]) if include_scope and row.get("scope_of_work") else None,
                note=str(row["note"]) if row.get("note") else None,
            )
            parts.append(
                "<tr>"
                f"<td width=\"{_LABEL_COL_WIDTH}\" class=\"proposal-fee-service\" "
                f"style=\"width:{_LABEL_COL_WIDTH}\">{service_html}</td>"
                + _amount_cell(cols.get("monthly"), currency, include_currency=bool(currency), compact_layout=True)
                + _amount_cell(cols.get("quarterly"), currency, include_currency=bool(currency), compact_layout=True)
                + _amount_cell(cols.get("annual"), currency, include_currency=bool(currency), compact_layout=True)
                + _amount_cell(cols.get("once_off"), currency, include_currency=bool(currency), compact_layout=True)
                + _amount_cell(total, currency, include_currency=bool(currency), compact_layout=True)
                + "</tr>"
            )
            sub += 1
        parts.append("</tbody></table>")
        parts.append("")
    return "\n".join(parts).strip()


def render_simple_table(
    groups: list[dict[str, Any]],
    *,
    show_recurring: bool = True,
    include_scope: bool = False,
) -> str:
    parts: list[str] = []
    for group in groups:
        parts.append(f"### {group.get('display_name') or group.get('group_id')}")
        parts.append("")
        parts.append("<table class=\"proposal-fee-table proposal-fee-table-simple\">")
        parts.append("<thead><tr><th>Service</th><th>Amount</th></tr></thead><tbody>")
        for row in group.get("rows") or []:
            amount = row.get("amount")
            if amount is None:
                amount_text = str(row.get("status") or "TBD")
            else:
                row_currency = row.get("currency") or ""
                amount_text = format_money(float(amount), row_currency, include_currency=bool(row_currency)).strip()
            label = str(row.get("label") or row.get("sku"))
            if show_recurring and row.get("recurring") == "RECURRING":
                label = f"{label} ({str(row.get('billing_frequency', 'recurring')).lower()})"
            service_parts = [f"<strong>{escape_html(label)}</strong>"]
            if include_scope and row.get("scope_of_work"):
                scope_html = format_scope_html(str(row["scope_of_work"]))
                if scope_html:
                    service_parts.append(scope_html)
            service_html = "".join(service_parts)
            parts.append(
                "<tr>"
                f"<td class=\"proposal-fee-service\">{service_html}</td>"
                f"<td class=\"proposal-fee-amount\">{escape_html(amount_text)}</td>"
                "</tr>"
            )
        parts.append("</tbody></table>")
        parts.append("")
    return "\n".join(parts).strip()


def render_payment_options_table(options: list[dict[str, Any]], *, currency: str = "") -> str:
    if not options:
        return "_No payment options configured._"

    parts: list[str] = []
    for option in options:
        label = option.get("label") or option.get("option_id") or "Payment Option"
        parts.append(f"### {label}")
        parts.append("")
        parts.append("<table class=\"proposal-fee-table proposal-payment-table\">")
        parts.append(_payment_table_head())
        rows = option.get("rows") or []
        for index, row in enumerate(rows, 1):
            row_label = row.get("label") or row.get("group_id") or f"{index}."
            total = row.get("total_annualized")
            if total is None:
                total = row_total_annualized(row)
            parts.append(
                "<tr>"
                f"<td>{escape_html(str(row_label))}</td>"
                + _amount_cell(row.get("monthly"), currency, include_currency=bool(currency))
                + _amount_cell(row.get("quarterly"), currency, include_currency=bool(currency))
                + _amount_cell(row.get("annual"), currency, include_currency=bool(currency))
                + _amount_cell(row.get("once_off"), currency, include_currency=bool(currency))
                + _amount_cell(total, currency, include_currency=bool(currency))
                + "</tr>"
            )
        summary = option.get("summary") or payment_summary_footer(rows)
        once_off = format_money(summary.get("once_off_total"), currency, include_currency=bool(currency))
        recurring = format_money(summary.get("recurring_annualized_total"), currency, include_currency=bool(currency))
        parts.append(
            f"<tr class=\"proposal-fee-summary\">"
            f"<td colspan=\"5\">Once-Off Fees</td>"
            f"<td class=\"proposal-fee-amount\">{escape_html(once_off)}</td>"
            "</tr>"
        )
        parts.append(
            f"<tr class=\"proposal-fee-summary\">"
            f"<td colspan=\"5\">"
            "<strong>Annualised Total Fees</strong> "
            "<em>(billed on completion, with monthly, quarterly and annual fees associated)</em>"
            "</td>"
            f"<td class=\"proposal-fee-amount\"><strong>{escape_html(recurring)}</strong></td>"
            "</tr>"
        )
        parts.append("</tbody></table>")
        parts.append("")
    return "\n".join(parts).strip()
