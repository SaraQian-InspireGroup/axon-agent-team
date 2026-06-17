"""Proposal patch pipeline — expand selection, pricing, placeholders, completeness."""

from __future__ import annotations

from typing import Any

from app.proposal.catalog import expand_selected_skus, fetch_packages_by_ids, fetch_services_by_skus
from app.proposal.fee_table import (
    payment_summary_footer,
    render_frequency_table,
    render_payment_options_table,
    render_simple_table,
    row_frequency_columns,
    row_total_annualized,
    sum_group_columns,
)
from app.proposal.loaders import (
    get_category,
    load_knowledge_index,
    load_template_yaml,
    read_knowledge_file,
    read_static_block,
    resolve_document_title,
    resolve_template_id,
)
from app.proposal.pricing import compute_pricing
from app.proposal.state import get_path


def run_pipeline(state: dict[str, Any]) -> dict[str, Any]:
    meta = state.setdefault("proposal_meta", {})
    category_id = meta.get("category_id")
    if category_id and not meta.get("template_id"):
        cat = get_category(str(category_id))
        if cat and cat.get("default_template_id"):
            meta["template_id"] = cat["default_template_id"]

    template_id = resolve_template_id(state)
    services: list[dict[str, Any]] = []
    if category_id:
        skus = expand_selected_skus(str(category_id), state.get("selection") or {})
        selection = state.setdefault("selection", {})
        selection["expanded_skus"] = skus
        services = fetch_services_by_skus(str(category_id), skus)

    pricing_facts = state.get("pricing_facts") or {}
    overrides = (state.get("pricing") or {}).get("overrides") or {}
    computed, explanations, recurring = compute_pricing(services, pricing_facts, overrides)
    state.setdefault("pricing", {})
    state["pricing"]["computed"] = computed
    state["pricing"]["explanations"] = explanations
    state["pricing"]["recurring_schedule"] = recurring

    state["line_items"] = materialize_line_items(
        services,
        computed,
        template_id,
        state=state,
        category_id=str(category_id) if category_id else None,
    )
    state["payment_options"] = materialize_payment_options(state, state["line_items"])
    state["resolved_placeholders"] = resolve_placeholders(state, services, template_id)
    state["completeness"] = scan_completeness(state, template_id)
    meta["stage"] = derive_stage(state)
    return state


def _build_row(
    service: dict[str, Any],
    computed: dict[str, Any],
    *,
    include_scope: bool,
) -> dict[str, Any] | None:
    sku = service["sku"]
    price = computed.get(sku) or {}
    if price.get("status") == "not_applicable":
        return None
    row: dict[str, Any] = {
        "sku": sku,
        "label": service.get("service_name_on_proposal") or service.get("product_name"),
        "amount": price.get("amount"),
        "currency": price.get("currency") or service.get("price_currency"),
        "status": price.get("status"),
        "recurring": service.get("recurring"),
        "billing_frequency": service.get("billing_frequency"),
        "service_group": service.get("service_group"),
        "department_team": service.get("department_team"),
        "package_id": service.get("_package_id"),
    }
    row["frequency_columns"] = row_frequency_columns(row)
    if include_scope and service.get("scope_of_work"):
        row["scope_of_work"] = service["scope_of_work"]
    return row


def _group_services_by_package(
    services: list[dict[str, Any]],
    computed: dict[str, Any],
    *,
    category_id: str | None,
    selection: dict[str, Any],
    include_scope: bool,
    custom_groups: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    service_by_sku = {service["sku"]: service for service in services}
    expanded = [service["sku"] for service in services]

    if custom_groups:
        groups: list[dict[str, Any]] = []
        assigned: set[str] = set()
        for index, spec in enumerate(custom_groups, 1):
            group_id = str(spec.get("group_id") or f"table_{index}")
            rows: list[dict[str, Any]] = []
            for sku in spec.get("skus") or []:
                service = service_by_sku.get(str(sku))
                if not service:
                    continue
                row = _build_row(service, computed, include_scope=include_scope)
                if row:
                    rows.append(row)
                    assigned.add(str(sku))
            if rows:
                groups.append(
                    {
                        "group_id": group_id,
                        "display_name": spec.get("display_name") or group_id,
                        "rows": rows,
                    }
                )
        leftover = [sku for sku in expanded if sku not in assigned]
        if leftover:
            rows = []
            for sku in leftover:
                service = service_by_sku.get(sku)
                if not service:
                    continue
                row = _build_row(service, computed, include_scope=include_scope)
                if row:
                    rows.append(row)
            if rows:
                groups.append(
                    {
                        "group_id": "additional_services",
                        "display_name": "Additional services",
                        "rows": rows,
                    }
                )
        return groups

    package_ids = list(selection.get("selected_packages") or [])
    packages = fetch_packages_by_ids(category_id, package_ids) if category_id and package_ids else []
    sku_to_package: dict[str, dict[str, Any]] = {}
    for package in packages:
        for sku in package.get("linked_skus") or []:
            if sku in expanded and sku not in sku_to_package:
                sku_to_package[sku] = package

    groups = []
    for package in packages:
        rows: list[dict[str, Any]] = []
        for sku in package.get("linked_skus") or []:
            service = service_by_sku.get(sku)
            if not service:
                continue
            service = {**service, "_package_id": package["package_id"]}
            row = _build_row(service, computed, include_scope=include_scope)
            if row:
                rows.append(row)
        if rows:
            groups.append(
                {
                    "group_id": package["package_id"],
                    "display_name": package.get("package_name") or package["package_id"],
                    "rows": rows,
                }
            )

    adhoc_skus = [
        sku
        for sku in expanded
        if sku not in sku_to_package and sku in service_by_sku
    ]
    if adhoc_skus:
        rows = []
        for sku in adhoc_skus:
            row = _build_row(service_by_sku[sku], computed, include_scope=include_scope)
            if row:
                rows.append(row)
        if rows:
            if len(groups) == 1:
                groups[0]["rows"].extend(rows)
            else:
                groups.append(
                    {
                        "group_id": "additional_services",
                        "display_name": "Additional services",
                        "rows": rows,
                    }
                )
    elif not groups:
        rows = []
        for service in services:
            row = _build_row(service, computed, include_scope=include_scope)
            if row:
                rows.append(row)
        if rows:
            groups.append(
                {
                    "group_id": "professional_fees",
                    "display_name": "Professional fees",
                    "rows": rows,
                }
            )
    return groups


def materialize_line_items(
    services: list[dict[str, Any]],
    computed: dict[str, Any],
    template_id: str | None,
    *,
    state: dict[str, Any] | None = None,
    category_id: str | None = None,
) -> dict[str, Any]:
    if not services or not template_id:
        return {"groups": []}

    tpl = load_template_yaml(template_id)
    placeholder = (tpl.get("placeholders") or {}).get("solution_and_price") or {}
    layout = placeholder.get("fee_layout") or {}
    group_by = layout.get("group_by") or "service_group"
    include_scope = bool(placeholder.get("include_scope_of_work"))
    state = state or {}
    selection = state.get("selection") or {}
    custom_groups = (state.get("fee_layout") or {}).get("custom_groups")

    if group_by == "package":
        groups = _group_services_by_package(
            services,
            computed,
            category_id=category_id,
            selection=selection,
            include_scope=include_scope,
            custom_groups=custom_groups if isinstance(custom_groups, list) else None,
        )
        return {"groups": groups}

    buckets: dict[str, list[dict[str, Any]]] = {}
    group_labels: dict[str, str] = {}
    for service in services:
        row = _build_row(service, computed, include_scope=include_scope)
        if not row:
            continue
        group_key = str(service.get(group_by) or "other")
        group_labels[group_key] = (
            service.get("service_group_display")
            or service.get("department_team")
            or group_key.replace("_", " ").title()
        )
        buckets.setdefault(group_key, []).append(row)

    groups = [
        {
            "group_id": group_id,
            "display_name": group_labels.get(group_id, group_id),
            "rows": rows,
        }
        for group_id, rows in buckets.items()
    ]
    return {"groups": groups}


def materialize_payment_options(state: dict[str, Any], line_items: dict[str, Any]) -> dict[str, Any]:
    writable = state.get("payment_options") or {}
    user_options = list(writable.get("options") or [])
    overrides = writable.get("overrides") or {}
    groups = line_items.get("groups") or []

    default_rows: list[dict[str, Any]] = []
    for index, group in enumerate(groups, 1):
        totals = sum_group_columns(group.get("rows") or [])
        row = {
            "group_id": group.get("group_id"),
            "label": group.get("display_name") or f"{index}. Services",
            **totals,
            "total_annualized": row_total_annualized(totals),
        }
        default_rows.append(row)

    default_option = {
        "option_id": "option_a",
        "label": "Payment Option A",
        "rows": default_rows,
        "summary": payment_summary_footer(default_rows),
    }

    if not user_options:
        resolved = [_apply_payment_overrides(default_option, overrides.get("option_a") or {})]
    else:
        resolved = []
        for option in user_options:
            merged = _merge_payment_option(option, default_option)
            resolved.append(_apply_payment_overrides(merged, overrides.get(option.get("option_id")) or {}))

    return {
        "options": user_options,
        "overrides": overrides,
        "resolved": resolved,
    }


def _merge_payment_option(user_option: dict[str, Any], default_option: dict[str, Any]) -> dict[str, Any]:
    option_id = user_option.get("option_id") or default_option.get("option_id")
    label = user_option.get("label") or default_option.get("label")
    user_rows = user_option.get("rows") or []
    if not user_rows:
        rows = [dict(row) for row in default_option.get("rows") or []]
    else:
        default_by_group = {
            str(row.get("group_id")): row for row in default_option.get("rows") or [] if row.get("group_id")
        }
        rows = []
        for row in user_rows:
            base = dict(default_by_group.get(str(row.get("group_id")), {}))
            base.update({k: v for k, v in row.items() if v is not None})
            if base.get("total_annualized") is None:
                base["total_annualized"] = row_total_annualized(base)
            rows.append(base)
    summary = payment_summary_footer(rows)
    return {"option_id": option_id, "label": label, "rows": rows, "summary": summary}


def _apply_payment_overrides(option: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    if not overrides:
        return option
    merged = dict(option)
    row_overrides = overrides.get("rows") or {}
    rows = []
    for row in option.get("rows") or []:
        patch = row_overrides.get(row.get("group_id")) or {}
        updated = {**row, **{k: v for k, v in patch.items() if v is not None}}
        updated["total_annualized"] = row_total_annualized(updated)
        rows.append(updated)
    merged["rows"] = rows
    if overrides.get("label"):
        merged["label"] = overrides["label"]
    merged["summary"] = payment_summary_footer(rows)
    return merged


def _selected_service_groups(services: list[dict[str, Any]]) -> set[str]:
    groups: set[str] = set()
    for service in services:
        group = service.get("service_group")
        if group:
            groups.add(str(group))
    return groups


def _optional_section_enabled(
    section: dict[str, Any],
    *,
    service_groups: set[str],
    enabled_sections: set[str],
) -> bool:
    trigger = section.get("trigger") or {}
    any_of = trigger.get("any_of") or []
    if not any_of:
        return False
    for clause in any_of:
        clause_groups = set(clause.get("service_groups") or [])
        clause_enabled = set(clause.get("enabled_sections") or [])
        if clause_groups & service_groups:
            return True
        if clause_enabled & enabled_sections:
            return True
    return False


def _resolve_knowledge_entries(
    state: dict[str, Any],
    services: list[dict[str, Any]],
    *,
    kind_filter: str | None = None,
) -> list[dict[str, Any]]:
    index = load_knowledge_index()
    entries = index.get("entries") or {}
    triggers = index.get("triggers") or []
    category_id = (state.get("proposal_meta") or {}).get("category_id")
    service_groups = _selected_service_groups(services)
    matched_ids: list[str] = []

    for trigger in triggers:
        match = trigger.get("match") or {}
        if match.get("category_id") and match["category_id"] != category_id:
            continue
        match_group = match.get("service_group")
        if match_group and match_group not in service_groups:
            continue
        matched_ids.extend(trigger.get("add") or [])

    seen: set[str] = set()
    resolved: list[dict[str, Any]] = []
    for entry_id in matched_ids:
        if entry_id in seen:
            continue
        seen.add(entry_id)
        entry = entries.get(entry_id)
        if not entry:
            continue
        if kind_filter and entry.get("kind") != kind_filter:
            continue
        try:
            body = read_knowledge_file(str(entry["path"]))
        except (OSError, ValueError):
            body = ""
        resolved.append(
            {
                "id": entry_id,
                "kind": entry.get("kind"),
                "title": entry.get("title") or entry_id,
                "path": entry.get("path"),
                "body": body,
            }
        )
    return resolved


def _resolve_fee_description(state: dict[str, Any], template_id: str | None, spec: dict[str, Any]) -> str:
    override = state.get("fee_description")
    if isinstance(override, str) and override.strip():
        return override.strip()
    fee_spec = spec.get("fee_description") or {}
    file_ref = fee_spec.get("file")
    if file_ref and template_id:
        try:
            return read_static_block(template_id, str(file_ref)).strip()
        except OSError:
            return ""
    return ""


def render_solution_and_price(state: dict[str, Any], template_id: str | None) -> str:
    line_items = state.get("line_items") or {}
    groups = line_items.get("groups") or []
    if not groups:
        selection = state.get("selection") or {}
        if selection.get("selected_packages") or selection.get("selected_skus"):
            return "_Pricing pending — check pricing_facts or missing catalog rows._"
        return "_No services selected yet._"

    tpl = load_template_yaml(template_id) if template_id else {}
    placeholder = (tpl.get("placeholders") or {}).get("solution_and_price") or {}
    layout = placeholder.get("fee_layout") or {}
    table_style = layout.get("table_style") or "simple_amount"
    show_recurring = layout.get("show_recurring", True)
    include_scope = bool(placeholder.get("include_scope_of_work"))
    currency = layout.get("currency") or _default_currency(groups)

    parts: list[str] = []
    fee_description = _resolve_fee_description(state, template_id, placeholder)
    if fee_description:
        parts.append(fee_description)
        parts.append("")

    if table_style == "frequency_columns":
        parts.append(
            render_frequency_table(groups, currency=currency, include_scope=include_scope)
        )
    else:
        parts.append(
            render_simple_table(
                groups,
                show_recurring=show_recurring,
                include_scope=include_scope,
            )
        )
    return "\n".join(parts).strip()


def _default_currency(groups: list[dict[str, Any]]) -> str:
    for group in groups:
        for row in group.get("rows") or []:
            currency = row.get("currency")
            if currency:
                return str(currency)
    return ""


def render_payment_options(state: dict[str, Any], template_id: str | None) -> str:
    payment = state.get("payment_options") or {}
    options = payment.get("resolved") or []
    if not options:
        return "_Payment options will appear once services are selected._"

    tpl = load_template_yaml(template_id) if template_id else {}
    layout = (
        (tpl.get("placeholders") or {}).get("solution_and_price") or {}
    ).get("fee_layout") or {}
    currency = layout.get("currency") or "AUD"
    intro_spec = (tpl.get("placeholders") or {}).get("payment_options") or {}
    intro_file = intro_spec.get("intro_file")
    parts: list[str] = []
    if intro_file and template_id:
        try:
            parts.append(read_static_block(template_id, str(intro_file)).strip())
            parts.append("")
        except OSError:
            pass
    parts.append(render_payment_options_table(options, currency=currency))
    return "\n".join(parts).strip()


def render_required_docs(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "_No required documents for current selection._"
    parts: list[str] = []
    for entry in entries:
        title = entry.get("title") or entry.get("id")
        body = (entry.get("body") or "").strip()
        parts.append(f"- **{title}**")
        if body:
            parts.append("")
            parts.append(body)
        parts.append("")
    return "\n".join(parts).strip()


def resolve_placeholders(
    state: dict[str, Any],
    services: list[dict[str, Any]],
    template_id: str | None,
) -> dict[str, Any]:
    if not template_id:
        return {}

    tpl = load_template_yaml(template_id)
    placeholders = tpl.get("placeholders") or {}
    optional_sections = tpl.get("optional_sections") or []
    service_groups = _selected_service_groups(services)
    enabled_sections = set(state.get("enabled_sections") or [])
    active_optional = {
        section["id"]
        for section in optional_sections
        if section.get("id")
        and _optional_section_enabled(
            section,
            service_groups=service_groups,
            enabled_sections=enabled_sections,
        )
    }
    state["active_optional_sections"] = sorted(active_optional)

    resolved: dict[str, Any] = {
        "document_title": {
            "filled": True,
            "value": resolve_document_title(state, template_id),
        }
    }
    doc_entries = _resolve_knowledge_entries(state, services, kind_filter="required_doc")

    for key, spec in placeholders.items():
        ptype = spec.get("type")
        if ptype == "state":
            value = get_path(state, str(spec.get("path") or key))
            resolved[key] = {"filled": bool(value), "value": value}
        elif ptype == "static":
            optional_id = next(
                (
                    section.get("id")
                    for section in optional_sections
                    if section.get("placeholder") == key
                ),
                None,
            )
            if optional_id and optional_id not in active_optional:
                resolved[key] = {"filled": True, "value": "", "skipped_optional": True}
                continue
            try:
                content = read_static_block(template_id, str(spec.get("file")))
                resolved[key] = {"filled": bool(content.strip()), "value": content}
            except OSError:
                resolved[key] = {"filled": False, "value": ""}
        elif ptype == "solution_and_price":
            content = render_solution_and_price(state, template_id)
            has_selection = bool((state.get("selection") or {}).get("expanded_skus"))
            missing_facts = any(
                (v or {}).get("status") == "missing_facts"
                for v in (state.get("pricing") or {}).get("computed", {}).values()
            )
            resolved[key] = {
                "filled": has_selection and not missing_facts,
                "value": content,
                "missing_facts": missing_facts,
            }
        elif ptype == "payment_options":
            if "payment_options" not in active_optional:
                resolved[key] = {"filled": True, "value": "", "skipped_optional": True}
                continue
            content = render_payment_options(state, template_id)
            resolved[key] = {
                "filled": bool((state.get("line_items") or {}).get("groups")),
                "value": content,
            }
        elif ptype == "knowledge":
            if spec.get("resolver") == "triggered":
                content = render_required_docs(doc_entries)
                resolved[key] = {"filled": bool(doc_entries), "value": content, "entries": doc_entries}
            else:
                picked = (state.get("peripheral") or {}).get(key.split(".", 1)[-1])
                resolved[key] = {"filled": bool(picked), "value": picked}
        elif ptype == "session":
            path = str(spec.get("path") or key.split(".", 1)[-1])
            value = state.get(path) if "." not in path else get_path(state, path)
            if key == "session.appendix" and "appendix" not in active_optional:
                resolved[key] = {"filled": True, "value": "", "skipped_optional": True}
            else:
                resolved[key] = {"filled": bool(value), "value": value}
        else:
            resolved[key] = {"filled": False, "value": None}

    state.setdefault("peripheral", {})
    state["peripheral"]["required_docs"] = doc_entries
    return resolved


def scan_completeness(state: dict[str, Any], template_id: str | None) -> dict[str, Any]:
    if not template_id:
        return {
            "missing_required": ["proposal_meta.category_id"],
            "enabled_optional_unfilled": [],
            "ready_to_preview": False,
            "ready_to_generate": False,
        }

    tpl = load_template_yaml(template_id)
    placeholders = tpl.get("placeholders") or {}
    optional_sections = tpl.get("optional_sections") or []
    resolved = state.get("resolved_placeholders") or {}
    active_optional = set(state.get("active_optional_sections") or [])

    missing_required: list[str] = []
    for key, spec in placeholders.items():
        if not spec.get("required"):
            continue
        optional_id = next(
            (section.get("id") for section in optional_sections if section.get("placeholder") == key),
            None,
        )
        if optional_id and optional_id not in active_optional:
            continue
        entry = resolved.get(key) or {}
        if not entry.get("filled"):
            missing_required.append(key)

    enabled_optional_unfilled: list[str] = []
    for section in optional_sections:
        section_id = section.get("id")
        if not section_id or section_id not in active_optional:
            continue
        placeholder_key = section.get("placeholder")
        entry = resolved.get(str(placeholder_key)) or {}
        if not entry.get("filled") or not str(entry.get("value") or "").strip():
            enabled_optional_unfilled.append(str(section_id))

    ready = not missing_required
    return {
        "missing_required": missing_required,
        "enabled_optional_unfilled": enabled_optional_unfilled,
        "ready_to_preview": ready,
        "ready_to_generate": ready and not enabled_optional_unfilled,
    }


def derive_stage(state: dict[str, Any]) -> str:
    meta = state.get("proposal_meta") or {}
    if not meta.get("category_id"):
        return "INTAKE"
    client = state.get("client") or {}
    selection = state.get("selection") or {}
    completeness = state.get("completeness") or {}
    if completeness.get("ready_to_generate"):
        return "REVIEW"
    if selection.get("expanded_skus"):
        computed = (state.get("pricing") or {}).get("computed") or {}
        if any(v.get("status") == "missing_facts" for v in computed.values()):
            return "SCOPING"
        if computed:
            return "PRICING"
        return "SELECTION"
    if client.get("company_name") or client.get("contract_name"):
        return "SCOPING"
    return "INTAKE"
