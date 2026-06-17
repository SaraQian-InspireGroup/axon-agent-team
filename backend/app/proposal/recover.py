"""Recover proposal_state from persisted tool_result rows when session_state is empty."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.db.repositories.messages import MessageRepository
from app.proposal.schema import empty_proposal_state, writable_snapshot


def _parse_tool_payload(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def proposal_state_from_tool_result(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("status") == "error" or payload.get("error"):
        return None
    if not payload.get("patched"):
        return None

    raw_state = payload.get("state")
    if not isinstance(raw_state, dict):
        return None

    state = writable_snapshot(raw_state)
    meta = state.get("proposal_meta") or {}
    selection = state.get("selection") or {}
    if not (
        meta.get("category_id")
        or selection.get("selected_packages")
        or selection.get("selected_skus")
    ):
        return None
    return state


def extract_patch_result_from_row(row: Any) -> dict[str, Any] | None:
    meta = getattr(row, "message_metadata", None) or {}
    if meta.get("tool_name") != "patch_proposal_state":
        return None
    if getattr(row, "message_type", None) != "tool_result":
        return None

    content_payload = _parse_tool_payload(getattr(row, "content", None))
    if content_payload is not None:
        return proposal_state_from_tool_result(content_payload)

    meta_payload = _parse_tool_payload(meta.get("result"))
    if meta_payload is not None:
        return proposal_state_from_tool_result(meta_payload)
    return None


async def recover_proposal_state_from_messages(
    messages: MessageRepository,
    chat_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Return the latest successful patch_proposal_state snapshot, if any."""
    rows = await messages.list_by_chat(chat_id)
    for row in reversed(rows):
        recovered = extract_patch_result_from_row(row)
        if recovered is not None:
            return recovered
    return None
