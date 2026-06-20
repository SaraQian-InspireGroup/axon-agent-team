"""Proposal composer builtin tools."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Annotated, Any

from agent_framework import tool

from app.proposal.artifact_spec import ArtifactKind, ArtifactSpec
from app.proposal.context import get_run_proposal_state
from app.proposal.draft import (
    DraftPatchError,
    add_package_to_draft,
    add_services_to_draft,
    build_draft_preview,
    enable_draft_section,
    materialize_draft,
    patch_draft,
    render_draft_markdown,
)
from app.proposal.loaders import load_templates, read_knowledge_file
from app.proposal.paths import KNOWLEDGE_ROOT, PERIPHERAL_ROOT, TEMPLATES_ROOT
from app.proposal.storage import new_artifact_id, save_markdown

_PREVIEW_CHAR_LIMIT = 1200
logger = logging.getLogger(__name__)


def _resolve_pointer(state: dict[str, Any], pointer: str) -> Any:
    if pointer == "":
        return state
    if not pointer.startswith("/"):
        raise ValueError("JSON Pointer must start with '/'.")
    value: Any = state
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise ValueError(f"Cannot resolve through non-container at {part!r}.")
    return value


def _decode_json_string(value: Any, field_name: str) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be JSON object/array data, not an invalid JSON string") from exc


def _coerce_object(value: Any, field_name: str) -> dict[str, Any]:
    decoded = _decode_json_string(value, field_name)
    if not isinstance(decoded, dict):
        raise ValueError(f"{field_name} must be an object")
    return decoded


def _coerce_object_list(value: Any, field_name: str) -> list[dict[str, Any]]:
    decoded = _decode_json_string(value, field_name)
    if isinstance(decoded, dict):
        return [decoded]
    if not isinstance(decoded, list):
        raise ValueError(f"{field_name} must be an array of objects")
    bad_index = next((idx for idx, item in enumerate(decoded) if not isinstance(item, dict)), None)
    if bad_index is not None:
        raise ValueError(f"{field_name}[{bad_index}] must be an object")
    return decoded


def _is_allowed_knowledge_path(rel: str, full: Path) -> bool:
    """peripheral/* and template contracts/blocks under knowledge/."""
    peripheral = PERIPHERAL_ROOT.resolve()
    templates = TEMPLATES_ROOT.resolve()
    if str(full).startswith(str(peripheral)):
        return True
    if str(full).startswith(str(templates)):
        parts = [p for p in rel.split("/") if p]
        # templates/{template_id}/template.yaml or templates/{template_id}/blocks/...
        return (
            len(parts) == 3
            and parts[0] == "templates"
            and parts[2] == "template.yaml"
        ) or (
            len(parts) >= 4
            and parts[0] == "templates"
            and parts[2] == "blocks"
        )
    return False


def _validate_read_path(relative_path: str) -> None:
    rel = relative_path.strip().lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("Invalid path")
    full = (KNOWLEDGE_ROOT / rel).resolve()
    root = KNOWLEDGE_ROOT.resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Path escapes knowledge root")
    if not _is_allowed_knowledge_path(rel, full):
        raise ValueError("Path must be under peripheral/, templates/{template_id}/template.yaml, or templates/{template_id}/blocks/")


@tool(
    name="list_templates",
    description=(
        "List available proposal templates and their MDM catalog filters. "
        "Use when the user has not clearly chosen a proposal type, or asks what "
        "proposal types are supported. Do not use for service/package lookup."
    ),
)
def list_templates() -> dict[str, Any]:
    templates = load_templates()
    return {
        "templates": [
            {
                "template_id": row.get("template_id"),
                "display_name": row.get("display_name"),
                "catalog_filter": row.get("catalog_filter"),
            }
            for row in templates
        ]
    }


@tool(
    name="read_knowledge",
    description=(
        "Read text from knowledge/: peripheral/ (markdown, CSV, etc.) or "
        "templates/{template_id}/ (template.yaml, blocks/*.md). "
        "Use template.yaml to understand draft section ids/kinds/editability/derivations; "
        "use blocks/peripheral files for reusable proposal content. "
        "SKU/package pricing comes from Postgres MCP, not this tool."
    ),
)
def read_knowledge(
    path: Annotated[
        str,
        (
            "Relative path under knowledge/, e.g. "
            "templates/au-advisory/template.yaml, "
            "templates/harneys-bvi/blocks/terms-bvi.md, "
            "peripheral/required-docs/BVI/passport.md"
        ),
    ],
) -> dict[str, Any]:
    try:
        _validate_read_path(path)
        content = read_knowledge_file(path)
        return {"path": path, "content": content}
    except (OSError, ValueError) as exc:
        return {"path": path, "error": str(exc)}


@tool(
    name="initialize_proposal_draft",
    description=(
        "Create or reset the editable proposal draft from a chosen template. "
        "Use once after the template is known, or when the user explicitly switches "
        "template. This materializes template sections and preserves existing client "
        "facts when possible. Do not use for normal edits to an existing draft."
    ),
)
def initialize_proposal_draft(
    template_id: Annotated[str, "Proposal template_id, e.g. au-advisory."],
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    client = (ctx.draft or {}).get("facts", {}).get("client") or {}
    try:
        ctx.draft = materialize_draft(
            template_id=template_id,
            client=copy.deepcopy(client),
        )
        ctx.mark_draft_dirty()
        preview = build_draft_preview(ctx.draft)
        return {
            "status": "ok",
            "draft": copy.deepcopy(ctx.draft),
            "preview_status": preview.get("status"),
        }
    except Exception as exc:
        logger.exception("initialize_proposal_draft failed")
        return {"status": "error", "error": str(exc) or type(exc).__name__}


@tool(
    name="get_proposal_draft",
    description=(
        "Read the editable proposal draft that renders the right-hand Proposal Preview. "
        "Use before patching when you need exact section/table/row indexes or ids. "
        "Panel labels like 2.2 are render-time only (not stored in draft); map them to "
        "tables[]/rows[] per proposal-composer skill fee-table-display-index before patch. "
        "Omit path for the full draft; pass a JSON Pointer for a subtree."
    ),
)
def get_proposal_draft(
    path: Annotated[str | None, "Optional JSON Pointer, e.g. /document/sections."] = None,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    if ctx.draft is None:
        return {"status": "empty", "draft": None}
    if path:
        try:
            value = _resolve_pointer(ctx.draft, path)
        except Exception as exc:
            return {"status": "error", "path": path, "error": str(exc)}
        return {"status": "ok", "path": path, "value": copy.deepcopy(value)}
    return {"status": "ok", "draft": copy.deepcopy(ctx.draft)}


@tool(
    name="patch_proposal_draft",
    description=(
        "Apply RFC 6902 JSON Patch to existing proposal draft nodes. Use for visible "
        "display edits: client facts, section content, table titles, fee row service_name, "
        "scope_of_work, price.amount (numeric total), price.fee_raw (non-FIXED display text), "
        "or row/table ordering. If adding an MDM package or "
        "service, use add_package_to_proposal_draft/add_services_to_proposal_draft instead "
        "so catalog fields and provenance are materialized correctly. JSON Patch replace "
        "requires the target path to already exist; use add for new fields, and read the "
        "draft first with get_proposal_draft when unsure."
    ),
)
def patch_proposal_draft(
    patch: Annotated[
        list[dict[str, Any]],
        "RFC 6902 JSON Patch array targeting proposal_draft paths. Read draft first if indexes are unknown.",
    ]
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    if ctx.draft is None:
        return {"status": "error", "error": "Proposal draft is not initialized."}
    try:
        ctx.draft = patch_draft(ctx.draft, patch)
        if any(
            str(op.get("path") or "").startswith("/facts/client")
            for op in patch
            if isinstance(op, dict)
        ):
            from app.proposal.placeholders import sync_draft_template_placeholders

            ctx.draft = sync_draft_template_placeholders(ctx.draft)
        ctx.mark_draft_dirty()
        return {"status": "ok", "patched": True, "draft": copy.deepcopy(ctx.draft)}
    except DraftPatchError as exc:
        return {"status": "error", "http_status": 422, "error": exc.message}
    except Exception as exc:
        logger.exception("patch_proposal_draft failed")
        return {"status": "error", "error": str(exc) or type(exc).__name__}


@tool(
    name="add_package_to_proposal_draft",
    description=(
        "Materialize a confirmed MDM package into the draft fee section from rows already "
        "queried via MCP SQL. Pass the package row and its service rows, including description, "
        "department_team, pricing_type, price_amount, fee_raw, and footnotes; this tool does not "
        "query MDM. Do not use for renaming/editing an existing package table; patch the draft."
    ),
)
def add_package_to_proposal_draft(
    package: Annotated[Any, "MDM package row object, including package_id and package_name."],
    services: Annotated[
        Any,
        "Array of MDM service row objects returned for this package. Each row must include fields "
        "needed by the template fee_layout (typically description, department_team, pricing fields).",
    ],
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    if ctx.draft is None:
        return {"status": "error", "error": "Proposal draft is not initialized."}
    try:
        package_row = _coerce_object(package, "package")
        service_rows = _coerce_object_list(services, "services")
        ctx.draft = add_package_to_draft(ctx.draft, package_row, service_rows)
        ctx.mark_draft_dirty()
        return {"status": "ok", "draft": copy.deepcopy(ctx.draft)}
    except Exception as exc:
        logger.exception("add_package_to_proposal_draft failed")
        return {"status": "error", "error": str(exc) or type(exc).__name__}


@tool(
    name="add_services_to_proposal_draft",
    description=(
        "Materialize one or more confirmed MDM services/SKUs into the draft fee section from "
        "rows already queried via MCP SQL. Pass services as an array of row objects with "
        "pricing_type, price_amount, and fee_raw; a single service is represented as a one-item "
        "array. This tool does not query MDM. Do not use for editing service name, SOW, or price "
        "on existing rows; patch the draft."
    ),
)
def add_services_to_proposal_draft(
    services: Annotated[Any, "Array of MDM service row objects, each including sku, pricing fields, and display fields."],
    table_id: Annotated[str | None, "Optional fee table id. Existing table is reused; otherwise a new table is created."] = None,
    table_title: Annotated[str, "Title used only when a new fee table is created."] = "Additional services",
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    if ctx.draft is None:
        return {"status": "error", "error": "Proposal draft is not initialized."}
    try:
        service_rows = _coerce_object_list(services, "services")
        ctx.draft = add_services_to_draft(ctx.draft, service_rows, table_id=table_id, table_title=table_title)
        ctx.mark_draft_dirty()
        return {"status": "ok", "draft": copy.deepcopy(ctx.draft)}
    except Exception as exc:
        logger.exception("add_services_to_proposal_draft failed")
        return {"status": "error", "error": str(exc) or type(exc).__name__}


@tool(
    name="enable_proposal_draft_section",
    description=(
        "Enable or disable an optional draft section by section id, e.g. payment_options, "
        "credentials, or appendix. Use for optional/derived sections that already exist in "
        "the template. Do not use to create new arbitrary sections; patch or template changes "
        "are required for that."
    ),
)
def enable_proposal_draft_section(
    section_id: Annotated[str, "Draft section id, e.g. payment_options."],
    enabled: Annotated[bool, "Whether the section should be enabled."] = True,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "error": "Proposal context unavailable for this run."}
    if ctx.draft is None:
        return {"status": "error", "error": "Proposal draft is not initialized."}
    try:
        ctx.draft = enable_draft_section(ctx.draft, section_id, enabled=enabled)
        ctx.mark_draft_dirty()
        return {"status": "ok", "draft": copy.deepcopy(ctx.draft)}
    except DraftPatchError as exc:
        return {"status": "error", "http_status": 422, "error": exc.message}
    except Exception as exc:
        logger.exception("enable_proposal_draft_section failed")
        return {"status": "error", "error": str(exc) or type(exc).__name__}


def _artifact_download_url(chat_id, artifact_id: str) -> str:
    return f"/api/v1/chats/{chat_id}/artifacts/{artifact_id}"


def _build_artifact_spec(
    *,
    kind: ArtifactKind,
    title: str,
    content: str,
    filename: str,
    chat_id,
    persist: bool,
) -> ArtifactSpec:
    artifact_id = new_artifact_id()
    download_url = None
    if persist and chat_id is not None:
        save_markdown(chat_id, artifact_id, content, filename=filename)
        download_url = _artifact_download_url(chat_id, artifact_id)
    preview_truncated = len(content) > _PREVIEW_CHAR_LIMIT
    return ArtifactSpec(
        kind=kind,
        title=title,
        content=content,
        filename=filename,
        artifact_id=artifact_id,
        download_url=download_url,
        preview_truncated=preview_truncated,
    )


def _queue_artifact(spec: ArtifactSpec) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "message": "Proposal context unavailable for this run."}
    queued = ctx.queue_artifact(spec)
    payload = spec.model_dump(mode="json")
    payload["status"] = "queued" if queued else "deduplicated"
    payload["queued"] = queued
    return payload


@tool(
    name="render_preview",
    description=(
        "Return a lightweight status for the current proposal draft preview. The UI already "
        "auto-renders after draft write tools, so call this only when you need to confirm "
        "preview/readiness status for your response. Do not call repeatedly after every patch."
    ),
)
def render_preview(
    draft: Annotated[bool, "Deprecated compatibility flag; draft preview is always used."] = False,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "message": "Proposal context unavailable for this run."}

    if ctx.draft is None:
        return {
            "status": "empty",
            "message": "Proposal draft is not initialized.",
            "missing_required": [],
        }

    preview = build_draft_preview(ctx.draft)
    return {
        "status": preview.get("status") or "ok",
        "message": "Live proposal panel updates automatically after draft changes.",
        "title": preview.get("title"),
        "state_fingerprint": preview.get("state_fingerprint"),
        "completeness": preview.get("completeness"),
        "missing_required": (preview.get("completeness") or {}).get("missing_required") or [],
    }


@tool(
    name="generate_document",
    description=(
        "Create a downloadable proposal markdown file from the current draft. Use only when "
        "the user asks to export/download/send/finalize a proposal. The live Proposal panel "
        "already shows the draft, so do not use this for ordinary preview. If blocked for "
        "missing required content, ask for the missing business information or use force only "
        "when the user explicitly accepts an incomplete file."
    ),
)
def generate_document(
    force: Annotated[bool, "If true, generate even when the draft is not ready_to_generate. Use only with user consent."] = False,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "message": "Proposal context unavailable for this run."}

    if ctx.draft is None:
        return {"status": "empty", "message": "Proposal draft is not initialized."}

    preview = build_draft_preview(ctx.draft)
    completeness = preview.get("completeness") or {}
    if not force and not completeness.get("ready_to_generate"):
        return {
            "status": "blocked",
            "message": "Proposal draft is not ready to generate.",
            "missing_required": completeness.get("missing_required") or [],
        }
    content = render_draft_markdown(ctx.draft)
    title = str((ctx.draft.get("meta") or {}).get("title") or "Proposal")
    spec = _build_artifact_spec(
        kind="proposal_document",
        title=title,
        content=content,
        filename=preview.get("filename") or "proposal.md",
        chat_id=ctx.chat_id,
        persist=True,
    )
    ctx.mark_draft_dirty()
    payload = _queue_artifact(spec)
    payload["download_url"] = spec.download_url
    payload["filename"] = spec.filename
    return payload
