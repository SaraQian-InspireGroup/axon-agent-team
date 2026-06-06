from typing import Any, Protocol


class ToolSlimmer(Protocol):
    def slim_tool_result(self, message_type: str, metadata: dict[str, Any], content: str | None) -> tuple[str | None, dict[str, Any]]:
        ...


class PassthroughToolSlimmer:
    """Phase 1: no slimming — cache projection equals source."""

    def slim_tool_result(
        self, message_type: str, metadata: dict[str, Any], content: str | None
    ) -> tuple[str | None, dict[str, Any]]:
        return content, metadata


class HistoryProjection:
    def __init__(self, slimmer: ToolSlimmer | None = None) -> None:
        self._slimmer = slimmer or PassthroughToolSlimmer()

    def project_for_cache(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        projected: list[dict[str, Any]] = []
        for row in rows:
            content, metadata = self._slimmer.slim_tool_result(
                row["message_type"], row.get("metadata") or {}, row.get("content")
            )
            projected.append({**row, "content": content, "metadata": metadata})
        return projected
