"""Resolve template.yaml placeholders from draft facts and fee tables."""

from __future__ import annotations

from typing import Any

from app.proposal.loaders import load_package_narratives_index, load_template_yaml, read_static_block


def _facts_value(draft: dict[str, Any], dotted_path: str) -> Any:
    if not dotted_path.startswith("/facts/"):
        return None
    value: Any = draft.get("facts") or {}
    for part in dotted_path[len("/facts/") :].split("/"):
        if not part:
            continue
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def selected_package_names(draft: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for section in (draft.get("document") or {}).get("sections") or []:
        if section.get("kind") != "fee_section":
            continue
        for table in section.get("tables") or []:
            title = str(table.get("title") or "").strip()
            source = table.get("source") or {}
            package_id = str(source.get("package_id") or "").strip()
            key = package_id or title
            if not key or key in seen:
                continue
            seen.add(key)
            names.append(title or package_id)
    return names


def _resolve_placeholder_value(
    spec: dict[str, Any],
    *,
    draft: dict[str, Any],
) -> str:
    draft_path = str(spec.get("draft_path") or "").strip()
    if draft_path == "derived":
        token = str(spec.get("token") or "")
        if token == "{{selected_packages_bullet_list}}":
            names = selected_package_names(draft)
            if not names:
                return str(spec.get("empty") or "—")
            return "\n".join(f"- {name}" for name in names)
        return ""

    value = _facts_value(draft, draft_path)
    if value not in (None, ""):
        return str(value)
    if spec.get("default") is not None:
        return str(spec["default"])
    return ""


def apply_template_placeholders(
    text: str,
    draft: dict[str, Any],
    template_id: str,
    context: str,
) -> str:
    """Replace tokens declared under template placeholders.{context}."""
    if not text or not template_id:
        return text
    tpl = load_template_yaml(template_id)
    specs = (tpl.get("placeholders") or {}).get(context) or []
    if not isinstance(specs, list):
        return text
    result = text
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        token = str(spec.get("token") or "")
        if not token or token not in result:
            continue
        result = result.replace(token, _resolve_placeholder_value(spec, draft=draft))
    return result


def placeholder_context_for_section(section: dict[str, Any]) -> str | None:
    section_id = str(section.get("id") or "")
    if section_id == "introduction":
        return "introduction"
    if section.get("kind") == "fee_section":
        return "fee_table"
    return None


def resolve_section_source_content(
    draft: dict[str, Any],
    section: dict[str, Any],
    *,
    template_id: str,
) -> str:
    """Load source-backed section text and apply placeholders."""
    edit_state = (section.get("edit_state") or {}).get("content")
    source = section.get("source") or {}
    file_ref = source.get("file")
    content = str(section.get("content") or "")
    if edit_state == "source" and file_ref:
        try:
            content = read_static_block(template_id, str(file_ref))
        except OSError:
            content = str(section.get("content") or "")
    context = placeholder_context_for_section(section)
    if context:
        content = apply_template_placeholders(content, draft, template_id, context)
    return content.strip()


def _narrative_index_entry(
    fee_section: dict[str, Any],
    template_id: str,
    package_id: str,
) -> tuple[dict[str, Any], str] | None:
    index_ref = str((fee_section.get("package_narratives") or {}).get("index") or "").strip()
    if not index_ref:
        return None
    try:
        index = load_package_narratives_index(template_id, index_ref)
    except (OSError, ValueError):
        return None
    entry = index.get(package_id)
    if not isinstance(entry, dict):
        return None
    file_ref = str(entry.get("file") or "").strip()
    if not file_ref:
        return None
    return entry, file_ref


def build_package_narrative_block(
    draft: dict[str, Any],
    fee_section: dict[str, Any],
    *,
    template_id: str,
    package_id: str,
    package_name: str,
) -> dict[str, Any] | None:
    """Materialize one editable package narrative block for fee_section.narratives."""
    resolved = _narrative_index_entry(fee_section, template_id, package_id)
    if resolved is None:
        return None
    entry, file_ref = resolved
    title = str(package_name or entry.get("package_name") or package_id).strip()
    content = ""
    try:
        content = read_static_block(template_id, file_ref).strip()
    except OSError:
        content = ""
    if content:
        content = apply_template_placeholders(content, draft, template_id, "fee_table")
    return {
        "id": f"narrative_{package_id}",
        "kind": "package_narrative",
        "package_id": package_id,
        "title": title,
        "content": content,
        "edit_state": {"content": "source" if content else "empty"},
        "source": {
            "type": "template_package_narrative",
            "package_id": package_id,
            "file": file_ref,
        },
        "policy": {"editable": True, "removable": True},
    }


def resolve_package_narrative_content(
    draft: dict[str, Any],
    narrative: dict[str, Any],
    *,
    template_id: str,
) -> str:
    edit_state = (narrative.get("edit_state") or {}).get("content")
    source = narrative.get("source") or {}
    file_ref = source.get("file")
    content = str(narrative.get("content") or "")
    if edit_state == "source" and file_ref:
        try:
            content = read_static_block(template_id, str(file_ref)).strip()
        except OSError:
            content = str(narrative.get("content") or "")
    return apply_template_placeholders(content, draft, template_id, "fee_table").strip()


def render_fee_section_narratives(
    draft: dict[str, Any],
    *,
    template_id: str,
    fee_section: dict[str, Any],
) -> str:
    """Concatenate package narrative blocks stored on the draft fee section."""
    parts: list[str] = []
    for narrative in fee_section.get("narratives") or []:
        if not isinstance(narrative, dict):
            continue
        body = resolve_package_narrative_content(draft, narrative, template_id=template_id)
        if body:
            parts.append(body)
    return "\n\n".join(parts).strip()


def _sync_fee_section_intro(
    draft: dict[str, Any],
    fee_section: dict[str, Any],
    *,
    template_id: str,
) -> None:
    intro = fee_section.get("intro") or {}
    if intro.get("edit_state") != "source":
        return
    source = intro.get("source") or {}
    file_ref = source.get("file")
    if not file_ref:
        return
    try:
        content = read_static_block(template_id, str(file_ref)).strip()
    except OSError:
        content = str(intro.get("content") or "")
    intro["content"] = apply_template_placeholders(content, draft, template_id, "fee_table")


def sync_draft_template_placeholders(draft: dict[str, Any]) -> dict[str, Any]:
    """Refresh source-backed sections after packages or client facts change."""
    template_id = str((draft.get("meta") or {}).get("template_id") or "").strip()
    if not template_id:
        return draft
    for section in (draft.get("document") or {}).get("sections") or []:
        if section.get("kind") == "fee_section":
            _sync_fee_section_intro(draft, section, template_id=template_id)
            for narrative in section.get("narratives") or []:
                if not isinstance(narrative, dict):
                    continue
                if (narrative.get("edit_state") or {}).get("content") != "source":
                    continue
                narrative["content"] = resolve_package_narrative_content(
                    draft,
                    narrative,
                    template_id=template_id,
                )
            continue
        if section.get("kind") != "markdown_block":
            continue
        edit_state = (section.get("edit_state") or {}).get("content")
        if edit_state != "source":
            continue
        resolved = resolve_section_source_content(draft, section, template_id=template_id)
        section["content"] = resolved
    return draft
