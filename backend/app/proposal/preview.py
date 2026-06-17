"""Live proposal preview payload (state → markdown + fingerprint)."""

from __future__ import annotations

import hashlib
import json
import copy
from typing import Any

from app.proposal.loaders import resolve_document_title, resolve_template_id
from app.proposal.rehydrate import rehydrate_proposal_state
from app.proposal.render import render_proposal_markdown
from app.proposal.state import empty_proposal_state
from app.proposal.storage import build_filename


def proposal_state_fingerprint(state: dict[str, Any]) -> str:
    """Stable hash for change detection and client cache invalidation."""
    payload = json.dumps(state, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _completeness_view(state: dict[str, Any]) -> dict[str, Any]:
    completeness = state.get("completeness") or {}
    return {
        "missing_required": list(completeness.get("missing_required") or []),
        "ready_to_preview": bool(completeness.get("ready_to_preview")),
        "ready_to_generate": bool(completeness.get("ready_to_generate")),
    }


def _document_title(state: dict[str, Any]) -> str:
    template_id = resolve_template_id(state)
    if template_id:
        try:
            return resolve_document_title(state, template_id)
        except (ValueError, OSError):
            pass
    company = (state.get("client") or {}).get("company_name")
    if company:
        return str(company)
    return "Proposal draft"


def build_live_preview(state: dict[str, Any] | None, *, draft: bool = True) -> dict[str, Any]:
    """Render current proposal state for the live artifact panel."""
    working = copy.deepcopy(state) if state is not None else empty_proposal_state()
    fingerprint = proposal_state_fingerprint(working)
    completeness = _completeness_view(working)
    title = _document_title(working)

    meta = working.get("proposal_meta") or {}
    selection = working.get("selection") or {}
    has_scope = bool(
        meta.get("category_id")
        or selection.get("selected_packages")
        or selection.get("selected_skus")
    )
    if not has_scope:
        return {
            "status": "empty",
            "title": title,
            "markdown": "",
            "filename": "proposal.md",
            "state_fingerprint": fingerprint,
            "message": "Select a region or services to start the proposal.",
            "completeness": completeness,
        }

    if rehydrate_proposal_state(working):
        fingerprint = proposal_state_fingerprint(working)
        completeness = _completeness_view(working)
        title = _document_title(working)

    if not draft and not completeness.get("ready_to_preview"):
        return {
            "status": "blocked",
            "title": title,
            "markdown": "",
            "filename": build_filename(working) if resolve_template_id(working) else "proposal.md",
            "state_fingerprint": fingerprint,
            "message": "Required fields are missing for preview.",
            "completeness": completeness,
        }

    template_id = resolve_template_id(working)
    if not template_id:
        return {
            "status": "empty",
            "title": title,
            "markdown": "",
            "filename": "proposal.md",
            "state_fingerprint": fingerprint,
            "message": "Choose a proposal category to load a template.",
            "completeness": completeness,
        }

    try:
        markdown = render_proposal_markdown(working, template_id=template_id)
    except (ValueError, OSError) as exc:
        return {
            "status": "error",
            "title": title,
            "markdown": "",
            "filename": "proposal.md",
            "state_fingerprint": fingerprint,
            "message": str(exc) or "Failed to render proposal.",
            "completeness": completeness,
        }

    return {
        "status": "ok",
        "title": title,
        "markdown": markdown,
        "filename": build_filename(working, template_id=template_id),
        "state_fingerprint": fingerprint,
        "completeness": completeness,
    }
