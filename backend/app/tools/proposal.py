"""Proposal composer builtin tools."""

from __future__ import annotations

import logging
from typing import Any

from agent_framework import tool

from app.proposal.artifact_spec import ArtifactKind, ArtifactSpec
from app.proposal.context import get_run_proposal_state
from app.proposal.loaders import load_categories, read_knowledge_file
from app.proposal.paths import KNOWLEDGE_ROOT, PERIPHERAL_ROOT, TEMPLATES_ROOT
from app.proposal.pipeline import run_pipeline
from app.proposal.rehydrate import rehydrate_proposal_state
from app.proposal.render import render_proposal_markdown
from app.proposal.state import apply_patch
from app.proposal.storage import build_filename, new_artifact_id, save_markdown

_PREVIEW_CHAR_LIMIT = 1200
logger = logging.getLogger(__name__)


def _public_state_view(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_meta": state.get("proposal_meta"),
        "client": state.get("client"),
        "pricing_facts": state.get("pricing_facts"),
        "selection": state.get("selection"),
        "enabled_sections": state.get("enabled_sections"),
        "appendix": state.get("appendix"),
        "pricing": {
            "computed": (state.get("pricing") or {}).get("computed"),
            "overrides": (state.get("pricing") or {}).get("overrides"),
            "explanations": (state.get("pricing") or {}).get("explanations"),
            "recurring_schedule": (state.get("pricing") or {}).get("recurring_schedule"),
        },
        "line_items": state.get("line_items"),
        "peripheral": state.get("peripheral"),
        "resolved_placeholders": {
            key: {
                "filled": entry.get("filled"),
                "preview": _preview(entry.get("value")),
            }
            for key, entry in (state.get("resolved_placeholders") or {}).items()
        },
        "completeness": state.get("completeness"),
        "active_optional_sections": state.get("active_optional_sections"),
    }


def _preview(value: Any, limit: int = 240) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


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


@tool(
    name="list_categories",
    description="List proposal categories (region × BU) from categories.yaml with default templates.",
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
        "Read a markdown knowledge file under proposal-composer knowledge/. "
        "Allowed roots: peripheral/ and templates/*/blocks/."
    ),
)
def read_knowledge(path: str) -> dict[str, Any]:
    try:
        _validate_read_path(path)
        content = read_knowledge_file(path)
        return {"path": path, "content": content}
    except (OSError, ValueError) as exc:
        return {"path": path, "error": str(exc)}


@tool(
    name="get_proposal_state",
    description=(
        "Return current proposal state including resolved placeholders, "
        "pricing summary, and completeness."
    ),
)
def get_proposal_state() -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"error": "Proposal context unavailable for this run."}
    if rehydrate_proposal_state(ctx.state):
        ctx.mark_dirty()
    return _public_state_view(ctx.state)


@tool(
    name="patch_proposal_state",
    description=(
        "Patch writable proposal fields (client, selection, pricing_facts, proposal_meta, "
        "enabled_sections, appendix, pricing.overrides). Platform reruns pricing and "
        "placeholder resolution automatically. Supports semantic ops: set_category, set_client, "
        "select_packages, set_pricing_facts, enable_sections."
    ),
)
def patch_proposal_state(patch: dict[str, Any]) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None:
        return {"error": "Proposal context unavailable for this run.", "status": "error"}
    if not isinstance(patch, dict):
        return {"error": "patch must be a JSON object", "status": "error"}
    try:
        ctx.state = apply_patch(ctx.state, patch)
        run_pipeline(ctx.state)
        ctx.mark_dirty()
        view = _public_state_view(ctx.state)
        view["patched"] = True
        view["status"] = "ok"
        return view
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
        "Render the current proposal template to markdown and show a preview artifact in chat. "
        "Requires completeness.ready_to_preview unless draft=true."
    ),
)
def render_preview(draft: bool = False) -> dict[str, Any]:
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
        content = render_proposal_markdown(ctx.state)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    company = (ctx.state.get("client") or {}).get("company_name") or "Proposal"
    spec = _build_artifact_spec(
        kind="proposal_preview",
        title=f"Preview — {company}",
        content=content,
        filename=build_filename(ctx.state),
        chat_id=ctx.chat_id,
        persist=False,
    )
    ctx.state.setdefault("artifacts", {})["last_preview_id"] = spec.artifact_id
    ctx.mark_dirty()
    return _queue_artifact(spec)


@tool(
    name="generate_document",
    description=(
        "Generate a downloadable proposal markdown document. "
        "Requires completeness.ready_to_generate unless force=true."
    ),
)
def generate_document(force: bool = False) -> dict[str, Any]:
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
    spec = _build_artifact_spec(
        kind="proposal_document",
        title=f"Proposal — {company}",
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
