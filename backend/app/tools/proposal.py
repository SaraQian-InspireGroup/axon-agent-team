"""Proposal composer builtin tools."""

from __future__ import annotations

import copy
import logging
from typing import Annotated, Any

from agent_framework import tool

from app.proposal.artifact_spec import ArtifactKind, ArtifactSpec
from app.proposal.context import get_run_proposal_state
from app.proposal.loaders import load_categories, read_knowledge_file
from app.proposal.paths import KNOWLEDGE_ROOT, PERIPHERAL_ROOT, TEMPLATES_ROOT
from app.proposal.pipeline import run_pipeline
from app.proposal.preview import build_live_preview
from app.proposal.rehydrate import rehydrate_proposal_state
from app.proposal.render import render_proposal_markdown
from app.proposal.schema import PROPOSAL_STATE_SCHEMA, PatchValidationError, apply_json_patch, resolve_pointer
from app.proposal.storage import build_filename, new_artifact_id, save_markdown

_PREVIEW_CHAR_LIMIT = 1200
logger = logging.getLogger(__name__)


def _resolve_pointer(state: dict[str, Any], pointer: str) -> Any:
    return resolve_pointer(state, pointer)


def _validate_read_path(relative_path: str) -> None:
    rel = relative_path.strip().lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("Invalid path")
    full = (KNOWLEDGE_ROOT / rel).resolve()
    root = KNOWLEDGE_ROOT.resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Path escapes knowledge root")
    peripheral = PERIPHERAL_ROOT.resolve()
    templates = TEMPLATES_ROOT.resolve()
    if not (
        str(full).startswith(str(peripheral))
        or str(full).startswith(str(templates))
    ):
        raise ValueError("Path must be under peripheral/ or templates/*/blocks/")


def _patch_error_response(exc: PatchValidationError) -> dict[str, Any]:
    return {
        "status": "error",
        "http_status": 422,
        "errors": exc.errors,
        "error": str(exc),
    }


def _patch_ok_response(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "patched": True,
        "state": copy.deepcopy(state),
    }


@tool(
    name="list_categories",
    description=(
        "List proposal categories (region × BU) and default template IDs. "
        "Use when category is unset or the user asks what regions/BUs are available."
    ),
)
def list_categories() -> dict[str, Any]:
    categories = load_categories()
    return {
        "categories": [
            {
                "category_id": row.get("category_id"),
                "region": row.get("region"),
                "bu": row.get("bu"),
                "display_name": row.get("display_name"),
                "default_template_id": row.get("default_template_id"),
            }
            for row in categories
        ]
    }


@tool(
    name="read_knowledge",
    description=(
        "Read markdown from knowledge/ (peripheral/ or templates/*/blocks/). "
        "Use for terms, bios, and required-doc copy—not for SKU/package pricing."
    ),
)
def read_knowledge(
    path: Annotated[str, "Relative path under knowledge/, e.g. peripheral/required-docs/MY/director-id.md"],
) -> dict[str, Any]:
    try:
        _validate_read_path(path)
        content = read_knowledge_file(path)
        return {"path": path, "content": content}
    except (OSError, ValueError) as exc:
        return {"path": path, "error": str(exc)}


@tool(
    name="get_proposal_schema",
    description="Return the JSON Schema for proposal_state (editable vs readOnly fields).",
)
def get_proposal_schema() -> dict[str, Any]:
    return {"schema": PROPOSAL_STATE_SCHEMA}


@tool(
    name="get_proposal_state",
    description=(
        "Read proposal_state. Omit path for the full object; pass a JSON Pointer "
        "(e.g. /selection) to read a subtree."
    ),
)
def get_proposal_state(
    path: Annotated[
        str | None,
        "Optional JSON Pointer (/client, /selection, /completeness). Omit for full state.",
    ] = None,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"error": "Proposal context unavailable for this run."}
    if rehydrate_proposal_state(ctx.state):
        ctx.mark_dirty()
    if path:
        try:
            value = _resolve_pointer(ctx.state, path)
        except Exception as exc:
            return {"status": "error", "path": path, "error": str(exc)}
        return {"path": path, "value": copy.deepcopy(value)}
    return {"state": copy.deepcopy(ctx.state)}


@tool(
    name="patch_proposal_state",
    description=(
        "Apply RFC 6902 JSON Patch to proposal_state (add, remove, replace, move, copy, test). "
        "Only non-readOnly schema paths are allowed; readOnly fields are recomputed after write. "
        "Invalid patches return http_status 422 with structured errors."
    ),
)
def patch_proposal_state(
    patch: Annotated[
        list[dict[str, Any]],
        (
            "JSON Patch array. Examples: "
            '[{"op":"replace","path":"/proposal_meta/category_id","value":"au-services"}], '
            '[{"op":"add","path":"/selection/selected_skus/-","value":"AU-TAX"}], '
            '[{"op":"replace","path":"/client/company_name","value":"Acme Ltd"}].'
        ),
    ],
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"error": "Proposal context unavailable for this run.", "status": "error"}
    try:
        ctx.state = apply_json_patch(ctx.state, patch)
        run_pipeline(ctx.state)
        ctx.mark_dirty()
        return _patch_ok_response(ctx.state)
    except PatchValidationError as exc:
        return _patch_error_response(exc)
    except Exception as exc:
        logger.exception("patch_proposal_state failed")
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
        "Confirm the live proposal panel reflects current state (optional). "
        "The UI auto-renders from state after patches—do not call repeatedly for side-panel updates. "
        "Use draft=true when required fields are missing but the user wants to see a draft."
    ),
)
def render_preview(
    draft: Annotated[bool, "If true, preview even when completeness.ready_to_preview is false."] = False,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "message": "Proposal context unavailable for this run."}

    completeness = (ctx.state.get("completeness") or {})
    if not draft and not completeness.get("ready_to_preview"):
        return {
            "status": "blocked",
            "message": "Proposal is not ready to preview.",
            "missing_required": completeness.get("missing_required") or [],
        }

    try:
        if rehydrate_proposal_state(ctx.state):
            ctx.mark_dirty()
        preview = build_live_preview(ctx.state, draft=True)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    ctx.state.setdefault("artifacts", {})["last_preview_at"] = preview.get("state_fingerprint")
    return {
        "status": preview.get("status") or "ok",
        "message": "Live proposal panel updates automatically after state changes.",
        "title": preview.get("title"),
        "state_fingerprint": preview.get("state_fingerprint"),
        "completeness": preview.get("completeness"),
        "missing_required": (preview.get("completeness") or {}).get("missing_required") or [],
    }


@tool(
    name="generate_document",
    description=(
        "Create a downloadable proposal file for the client. "
        "Use when the user asks to export or download; the live Proposal panel already shows the draft. "
        "Blocked unless force=true when required fields are missing."
    ),
)
def generate_document(
    force: Annotated[bool, "If true, generate even when completeness.ready_to_generate is false."] = False,
) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"status": "error", "message": "Proposal context unavailable for this run."}

    completeness = ctx.state.get("completeness") or {}
    if not force and not completeness.get("ready_to_generate"):
        return {
            "status": "blocked",
            "message": "Proposal is not ready to generate.",
            "missing_required": completeness.get("missing_required") or [],
            "enabled_optional_unfilled": completeness.get("enabled_optional_unfilled") or [],
        }

    try:
        if rehydrate_proposal_state(ctx.state):
            ctx.mark_dirty()
        content = render_proposal_markdown(ctx.state)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    company = (ctx.state.get("client") or {}).get("company_name") or "Proposal"
    doc_title = (
        (ctx.state.get("resolved_placeholders") or {})
        .get("document_title", {})
        .get("value")
    ) or company
    spec = _build_artifact_spec(
        kind="proposal_document",
        title=str(doc_title),
        content=content,
        filename=build_filename(ctx.state),
        chat_id=ctx.chat_id,
        persist=True,
    )
    meta = ctx.state.setdefault("proposal_meta", {})
    meta["stage"] = "GENERATE"
    ctx.state.setdefault("artifacts", {})["last_document_id"] = spec.artifact_id
    ctx.mark_dirty()
    payload = _queue_artifact(spec)
    payload["download_url"] = spec.download_url
    payload["filename"] = spec.filename
    return payload
