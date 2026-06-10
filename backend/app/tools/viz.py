"""Platform visualization tool — LLM passes intent only; platform builds the spec."""

from __future__ import annotations

from typing import Literal

from agent_framework import tool

from app.viz.context import get_run_viz_state
from app.viz.pipeline import build_viz_from_rows
from app.viz.spec import VizIntent

_INTENT_LITERAL = Literal["auto", "trend", "matrix", "ranking", "detail", "none"]


@tool(
    name="suggest_visualization",
    description=(
        "Render a chart or table from the most recent SQL query result. "
        "Pass intent only (auto/trend/matrix/ranking/detail/none); "
        "the platform selects chart type and builds the visualization spec."
    ),
)
def suggest_visualization(
    intent: _INTENT_LITERAL = "auto",
    title: str | None = None,
    source_call_id: str | None = None,
) -> dict:
    state = get_run_viz_state()
    if state is None:
        return {
            "status": "skipped",
            "message": "Visualization context unavailable; describe findings in text.",
        }

    entry = state.resolve_entry(source_call_id)
    if entry is None:
        return {
            "status": "skipped",
            "message": "No SQL result cached yet. Run a query first, then call this tool.",
        }

    viz_intent: VizIntent = intent  # type: ignore[assignment]
    result = build_viz_from_rows(
        entry.rows,
        entry.columns,
        intent=viz_intent,
        title=title,
    )
    queued = state.queue_viz(result, source_call_id=entry.call_id)
    payload = result.to_tool_dict()
    payload["source_call_id"] = entry.call_id
    payload["row_count"] = len(entry.rows)
    payload["queued"] = queued
    if not queued and result.spec is not None:
        payload["status"] = "deduplicated"
        payload["message"] = (
            "An identical chart for this query is already shown or pending; "
            "interpret the existing visualization in your reply."
        )
        payload.pop("spec", None)
    return payload
