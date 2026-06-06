"""Shared helpers for postgres MCP run_query middleware."""


def is_postgres_run_query(tool_name: str) -> bool:
    """Match postgres MCP SQL tools across naming conventions."""
    if tool_name in (
        "query_data",
        "postgres_query_data",
        "query",
        "postgres_query",
        "mcp__postgres__query",
        "mcp__postgres__query_data",
        "mcp__postgres__run_query",
        "postgres_run_query",
    ):
        return True
    return ("postgres" in tool_name) and (
        tool_name.endswith("_query_data")
        or tool_name.endswith("__query_data")
        or tool_name.endswith("_query")
        or tool_name.endswith("__query")
        or tool_name.endswith("_run_query")
        or tool_name.endswith("__run_query")
    )
