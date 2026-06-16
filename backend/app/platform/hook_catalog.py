"""Platform hook catalog — reusable across agents; agents override params in profile.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agent_framework import FunctionMiddleware

from app.middleware.result_truncator import (
    DEFAULT_MAX_OBSERVATION_BYTES,
    ResultTruncatorMiddleware,
)
from app.middleware.sql_validator import SqlValidatorMiddleware
from app.middleware.sql_viz import SqlVizMiddleware

HookFactory = Callable[[dict[str, Any]], FunctionMiddleware]


@dataclass(frozen=True)
class HookSpec:
    description: str
    defaults: dict[str, Any] = field(default_factory=dict)
    factory: HookFactory | None = None


def _build_sql_validator(params: dict[str, Any]) -> FunctionMiddleware:
    return SqlValidatorMiddleware(max_rows=int(params["max_rows"]))


def _build_result_truncator(params: dict[str, Any]) -> FunctionMiddleware:
    return ResultTruncatorMiddleware(max_observation_bytes=int(params["max_observation_bytes"]))


# Register platform hooks here. Agents enable by name in profile.yaml hooks: section.
HOOK_CATALOG: dict[str, HookSpec] = {
    "sql_validator": HookSpec(
        description="Pre-tool: read-only SQL validation and LIMIT injection for SQL run_query tools",
        defaults={"max_rows": 2000},
        factory=_build_sql_validator,
    ),
    "result_truncator": HookSpec(
        description="Post-tool: truncate large SQL run_query results for the model",
        defaults={"max_observation_bytes": DEFAULT_MAX_OBSERVATION_BYTES},
        factory=_build_result_truncator,
    ),
    "sql_viz": HookSpec(
        description=(
            "Post-tool (register last in hooks): cache SQL rows for visualization tools. "
            "Charts render only when the model calls suggest_visualization "
            "(set auto: true to also auto-queue after each query). "
            "Requires list_sql_results and suggest_visualization in allowed_tools."
        ),
        defaults={"auto": False, "min_rows": 3},
        factory=lambda params: SqlVizMiddleware(
            auto=bool(params.get("auto", False)),
            min_rows=int(params.get("min_rows", 3)),
        ),
    ),
}


def merge_hook_params(name: str, overrides: dict[str, Any] | None) -> dict[str, Any]:
    spec = HOOK_CATALOG.get(name)
    if spec is None:
        return dict(overrides or {})
    merged = dict(spec.defaults)
    if overrides:
        merged.update(overrides)
    return merged


def build_hook_middleware(name: str, params: dict[str, Any]) -> FunctionMiddleware | None:
    spec = HOOK_CATALOG.get(name)
    if spec is None or spec.factory is None:
        return None
    return spec.factory(params)
