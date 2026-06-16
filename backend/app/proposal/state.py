"""Proposal state helpers — empty state, patch merge, derived-field guards."""

from __future__ import annotations

import copy
from typing import Any

DERIVED_TOP_LEVEL_KEYS = frozenset(
    {
        "pricing",
        "line_items",
        "resolved_placeholders",
        "completeness",
        "peripheral",
    }
)

DERIVED_PRICING_KEYS = frozenset({"computed", "explanations", "recurring_schedule"})


def empty_proposal_state() -> dict[str, Any]:
    return {
        "proposal_meta": {
            "stage": "INTAKE",
        },
        "client": {},
        "pricing_facts": {},
        "selection": {
            "selected_packages": [],
            "selected_skus": [],
        },
        "pricing": {
            "computed": {},
            "overrides": {},
            "explanations": {},
            "recurring_schedule": [],
        },
        "line_items": {"groups": []},
        "enabled_sections": [],
        "appendix": [],
        "resolved_placeholders": {},
        "completeness": {
            "missing_required": [],
            "enabled_optional_unfilled": [],
            "ready_to_preview": False,
            "ready_to_generate": False,
        },
    }


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if key in DERIVED_TOP_LEVEL_KEYS:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def apply_semantic_ops(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Expand shorthand patch ops before merge."""
    working = copy.deepcopy(state)
    op = patch.get("op")
    if op == "set_category":
        meta = working.setdefault("proposal_meta", {})
        if patch.get("category_id"):
            meta["category_id"] = patch["category_id"]
        if patch.get("template_id"):
            meta["template_id"] = patch["template_id"]
        elif patch.get("category_id"):
            meta.pop("template_id", None)
        return working
    if op == "set_client":
        working["client"] = {**working.get("client", {}), **(patch.get("client") or {})}
        return working
    if op == "select_packages":
        selection = working.setdefault("selection", {})
        selection["selected_packages"] = list(patch.get("package_ids") or [])
        if patch.get("selected_skus") is not None:
            selection["selected_skus"] = list(patch.get("selected_skus") or [])
        return working
    if op == "set_pricing_facts":
        working["pricing_facts"] = {
            **working.get("pricing_facts", {}),
            **(patch.get("pricing_facts") or {}),
        }
        return working
    if op == "enable_sections":
        enabled = set(working.get("enabled_sections") or [])
        enabled.update(patch.get("section_ids") or [])
        working["enabled_sections"] = sorted(enabled)
        return working
    return _deep_merge(working, {k: v for k, v in patch.items() if k != "op"})


def apply_patch(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if not patch:
        return state
    if patch.get("op"):
        return apply_semantic_ops(state, patch)
    merged = _deep_merge(state, patch)
    pricing_patch = patch.get("pricing") if isinstance(patch.get("pricing"), dict) else None
    if pricing_patch and "overrides" in pricing_patch:
        merged.setdefault("pricing", {})
        merged["pricing"]["overrides"] = {
            **state.get("pricing", {}).get("overrides", {}),
            **pricing_patch["overrides"],
        }
    return merged


def get_path(state: dict[str, Any], dotted: str) -> Any:
    cur: Any = state
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur
