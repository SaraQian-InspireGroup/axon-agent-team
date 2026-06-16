"""Rehydrate persisted proposal state after cold start."""

from __future__ import annotations

from typing import Any

from app.proposal.pipeline import run_pipeline


def should_rehydrate_proposal_state(state: dict[str, Any]) -> bool:
    meta = state.get("proposal_meta") or {}
    selection = state.get("selection") or {}
    return bool(
        meta.get("category_id")
        or selection.get("selected_packages")
        or selection.get("selected_skus")
    )


def rehydrate_proposal_state(state: dict[str, Any]) -> bool:
    """Recompute pricing, line_items, and placeholders from selection + MDM. Returns True if ran."""
    if not should_rehydrate_proposal_state(state):
        return False
    run_pipeline(state)
    return True
