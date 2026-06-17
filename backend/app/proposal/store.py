"""Persist proposal state inside chat session payload."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from app.proposal.context import export_proposal_state, get_run_proposal_state


PROPOSAL_STATE_KEY = "proposal_state"


def load_proposal_state_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    stored = payload.get(PROPOSAL_STATE_KEY)
    if not isinstance(stored, dict) or not stored:
        return None
    meta = stored.get("proposal_meta") or {}
    selection = stored.get("selection") or {}
    if not (
        meta.get("category_id")
        or selection.get("selected_packages")
        or selection.get("selected_skus")
    ):
        return None
    return stored


def merge_proposal_state_into_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ctx = get_run_proposal_state()
    if ctx is None or not ctx.dirty:
        return payload
    merged = dict(payload)
    merged[PROPOSAL_STATE_KEY] = export_proposal_state() or ctx.state
    return merged


async def persist_proposal_state_if_dirty(session_store, chat_id: uuid.UUID) -> None:
    """Persist dirty proposal state into chat session payload."""
    ctx = get_run_proposal_state()
    if ctx is None or not ctx.dirty:
        return
    await session_store.merge_extension(
        chat_id,
        PROPOSAL_STATE_KEY,
        copy.deepcopy(ctx.state),
    )
    ctx.dirty = False
