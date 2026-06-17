"""Proposal state — defaults and JSON Patch entrypoint."""

from __future__ import annotations

from typing import Any

from app.proposal.schema import (
    PatchValidationError,
    apply_json_patch,
    empty_proposal_state,
    get_path,
    resolve_pointer,
    validate_state,
    writable_snapshot,
)

__all__ = [
    "PatchValidationError",
    "apply_json_patch",
    "empty_proposal_state",
    "get_path",
    "resolve_pointer",
    "validate_state",
    "writable_snapshot",
]
