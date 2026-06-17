"""Builtin tool groups — agents enable via profile allowed_tools."""

from __future__ import annotations

from app.tools import BUILTIN_TOOLS

PROPOSAL_TOOL_NAMES = frozenset(
    {
        "list_categories",
        "read_knowledge",
        "get_proposal_schema",
        "get_proposal_state",
        "patch_proposal_state",
        "render_preview",
        "generate_document",
    }
)

VIZ_TOOL_NAMES = frozenset(
    {
        "list_sql_results",
        "suggest_visualization",
    }
)


def resolve_builtin_tools(allowed_tools: list[str], group: frozenset[str]) -> list:
    """Return MAF tool callables for allowed names in a builtin group."""
    allowed = set(allowed_tools or [])
    return [BUILTIN_TOOLS[name] for name in group if name in allowed and name in BUILTIN_TOOLS]
