"""Per-run proposal state context (mirrors viz RunVizState pattern)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


from app.proposal.artifact_spec import ArtifactSpec


@dataclass
class RunProposalState:
    chat_id: uuid.UUID | None = None
    state: dict[str, Any] = field(default_factory=dict)
    dirty: bool = False
    pending_artifacts: list[ArtifactSpec] = field(default_factory=list)
    emitted_artifacts: list[ArtifactSpec] = field(default_factory=list)

    def mark_dirty(self) -> None:
        self.dirty = True

    def queue_artifact(self, spec: ArtifactSpec) -> bool:
        key = (spec.kind, spec.title, spec.artifact_id)
        for existing in (*self.pending_artifacts, *self.emitted_artifacts):
            if (existing.kind, existing.title, existing.artifact_id) == key:
                return False
        self.pending_artifacts.append(spec)
        return True

    def drain_pending_artifacts(self) -> list[ArtifactSpec]:
        batch = list(self.pending_artifacts)
        self.pending_artifacts.clear()
        self.emitted_artifacts.extend(batch)
        return batch


_run_proposal_state: ContextVar[RunProposalState | None] = ContextVar(
    "run_proposal_state", default=None
)


def init_run_proposal_state(
    *,
    chat_id: uuid.UUID | None = None,
    initial_state: dict[str, Any] | None = None,
    rehydrate: bool = True,
) -> RunProposalState:
    from app.proposal.rehydrate import rehydrate_proposal_state
    from app.proposal.state import empty_proposal_state

    state = initial_state if initial_state is not None else empty_proposal_state()
    ctx = RunProposalState(chat_id=chat_id, state=state)
    if rehydrate and rehydrate_proposal_state(ctx.state):
        ctx.mark_dirty()
    _run_proposal_state.set(ctx)
    return ctx


def get_run_proposal_state() -> RunProposalState | None:
    return _run_proposal_state.get()


def reset_run_proposal_state() -> None:
    _run_proposal_state.set(None)


def export_proposal_state() -> dict[str, Any] | None:
    ctx = get_run_proposal_state()
    if ctx is None:
        return None
    return ctx.state
