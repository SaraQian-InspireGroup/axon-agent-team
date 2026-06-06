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
        description="Pre-tool: read-only SQL validation and LIMIT injection for postgres run_query",
        defaults={"max_rows": 2000},
        factory=_build_sql_validator,
    ),
    "result_truncator": HookSpec(
        description="Post-tool: truncate large postgres run_query results for the model",
        defaults={"max_observation_bytes": DEFAULT_MAX_OBSERVATION_BYTES},
        factory=_build_result_truncator,
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
