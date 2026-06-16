"""Proposal patch pipeline — expand selection, pricing, placeholders, completeness."""

from __future__ import annotations

from typing import Any

from app.proposal.catalog import expand_selected_skus, fetch_services_by_skus
from app.proposal.loaders import (
    get_category,
    load_knowledge_index,
    load_template_yaml,
    read_knowledge_file,
    read_static_block,
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

    state["line_items"] = materialize_line_items(services, computed, template_id)
    state["resolved_placeholders"] = resolve_placeholders(state, services, template_id)
    state["completeness"] = scan_completeness(state, template_id)
    meta["stage"] = derive_stage(state)
    return state


def materialize_line_items(
    services: list[dict[str, Any]],
    computed: dict[str, Any],
    template_id: str | None,
) -> dict[str, Any]:
    if not services or not template_id:
        return {"groups": []}

    tpl = load_template_yaml(template_id)
    placeholder = (tpl.get("placeholders") or {}).get("solution_and_price") or {}
    layout = placeholder.get("fee_layout") or {}
    group_by = layout.get("group_by") or "service_group"
    include_scope = bool(placeholder.get("include_scope_of_work"))

    buckets: dict[str, list[dict[str, Any]]] = {}
    group_labels: dict[str, str] = {}

    for service in services:
        sku = service["sku"]
        price = computed.get(sku) or {}
        if price.get("status") == "not_applicable":
            continue
        group_key = str(service.get(group_by) or "other")
        group_labels[group_key] = (
            service.get("service_group_display")
            or service.get("department_team")
            or group_key.replace("_", " ").title()
        )
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
        }
        if include_scope and service.get("scope_of_work"):
            row["scope_of_work"] = service["scope_of_work"]
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
    show_recurring = placeholder.get("fee_layout", {}).get("show_recurring", True)
    include_scope = bool(placeholder.get("include_scope_of_work"))

    parts: list[str] = []
    for group in groups:
        parts.append(f"### {group.get('display_name') or group.get('group_id')}")
        parts.append("")
        parts.append("| Service | Amount |")
        parts.append("| --- | --- |")
        for row in group.get("rows") or []:
            amount = row.get("amount")
            if amount is None:
                amount_text = row.get("status") or "TBD"
            else:
                currency = row.get("currency") or ""
                amount_text = f"{currency} {amount:,.2f}".strip()
            label = row.get("label") or row.get("sku")
            if show_recurring and row.get("recurring") == "RECURRING":
                label = f"{label} ({row.get('billing_frequency', 'recurring').lower()})"
            parts.append(f"| {label} | {amount_text} |")
            if include_scope and row.get("scope_of_work"):
                parts.append("")
                parts.append(f"_{row['scope_of_work']}_")
        parts.append("")
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

    resolved: dict[str, Any] = {}
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
    if client.get("company_name"):
        return "SCOPING"
    return "INTAKE"
