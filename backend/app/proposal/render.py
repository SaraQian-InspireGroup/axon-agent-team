"""Render proposal.md templates into markdown."""

from __future__ import annotations

import re
from typing import Any

from app.proposal.loaders import load_proposal_body, resolve_template_id
from app.proposal.state import get_path

_IF_PATTERN = re.compile(r"\{\{#if\s+([\w.]+)\}\}(.*?)\{\{/if\}\}", re.DOTALL)
_OPTIONAL_PATTERN = re.compile(r"\{\{#optional\s+(\w+)\}\}(.*?)\{\{/optional\}\}", re.DOTALL)
_PLACEHOLDER_PATTERN = re.compile(r"\{\{([^#/][^}]*)\}\}")


def _resolve_placeholder_value(state: dict[str, Any], key: str) -> str:
    resolved = state.get("resolved_placeholders") or {}
    entry = resolved.get(key.strip())
    if isinstance(entry, dict):
        value = entry.get("value")
        if value is None:
            return ""
        return str(value)
    if key.startswith("client."):
        value = get_path(state, key)
        return str(value) if value is not None else ""
    return ""


def render_proposal_markdown(state: dict[str, Any], *, template_id: str | None = None) -> str:
    template_id = template_id or resolve_template_id(state)
    if not template_id:
        raise ValueError("proposal_meta.template_id is required to render")

    body = load_proposal_body(template_id)
    active_optional = set(state.get("active_optional_sections") or [])

    def replace_optional(match: re.Match[str]) -> str:
        section_id = match.group(1)
        if section_id not in active_optional:
            return ""
        return match.group(2)

    body = _OPTIONAL_PATTERN.sub(replace_optional, body)

    def replace_if(match: re.Match[str]) -> str:
        path = match.group(1)
        value = get_path(state, path)
        if value:
            return match.group(2)
        return ""

    body = _IF_PATTERN.sub(replace_if, body)

    def replace_placeholder(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return _resolve_placeholder_value(state, key)

    body = _PLACEHOLDER_PATTERN.sub(replace_placeholder, body)
    return body.strip()
