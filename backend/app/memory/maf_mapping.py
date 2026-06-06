import json
from typing import Any

from agent_framework import Content, Message


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "chat_id": str(row.chat_id),
        "role": row.role,
        "content": row.content,
        "message_type": row.message_type,
        "metadata": row.message_metadata or {},
        "parent_id": str(row.parent_id) if row.parent_id else None,
        "sequence": row.sequence,
    }


def _row_to_content(row: dict[str, Any]) -> Content | None:
    message_type = row["message_type"]
    content = row.get("content") or ""
    metadata = row.get("metadata") or {}

    if message_type == "reasoning":
        return Content.from_text_reasoning(
            text=content,
            id=metadata.get("content_id"),
            protected_data=metadata.get("protected_data"),
            additional_properties={
                k: v for k, v in metadata.items() if k not in ("protected_data", "content_id")
            },
        )

    if message_type == "text":
        return Content.from_text(content)

    if message_type in ("tool_call", "mcp_call"):
        return Content.from_function_call(
            call_id=str(metadata.get("call_id") or row.get("id")),
            name=str(metadata.get("tool_name") or metadata.get("name") or "unknown"),
            arguments=metadata.get("arguments") or {},
        )

    return None


def to_maf_messages(rows: list[dict[str, Any]]) -> list[Message]:
    """Rebuild MAF history with Anthropic-compatible grouping.

    Assistant text/tool_use blocks are coalesced into one assistant message.
    Tool results immediately follow as separate tool-role messages.
    Duplicate tool rows (audit + persist) are skipped by call_id.
    """
    messages: list[Message] = []
    assistant_contents: list[Content] = []
    seen_tool_calls: set[str] = set()
    seen_tool_results: set[str] = set()

    def flush_assistant() -> None:
        nonlocal assistant_contents
        if assistant_contents:
            messages.append(Message(role="assistant", contents=list(assistant_contents)))
            assistant_contents = []

    for row in rows:
        message_type = row["message_type"]
        role = row["role"]
        metadata = row.get("metadata") or {}
        call_id = str(metadata.get("call_id") or "")

        if message_type == "text" and role == "user":
            flush_assistant()
            messages.append(Message(role="user", contents=[Content.from_text(row.get("content") or "")]))
            continue

        if message_type in ("tool_result", "mcp_result"):
            if call_id and call_id in seen_tool_results:
                continue
            if call_id:
                seen_tool_results.add(call_id)

            flush_assistant()
            result = metadata.get("result", row.get("content"))
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            messages.append(
                Message.from_dict(
                    {
                        "role": "tool",
                        "contents": [
                            {
                                "type": "function_result",
                                "call_id": call_id or row.get("id"),
                                "result": result,
                            }
                        ],
                    }
                )
            )
            continue

        if message_type.startswith("skill_"):
            flush_assistant()
            messages.append(
                Message(
                    role="tool",
                    contents=[Content.from_text(row.get("content") or json.dumps(metadata, ensure_ascii=False))],
                )
            )
            continue

        if message_type == "error":
            flush_assistant()
            messages.append(
                Message(role="assistant", contents=[Content.from_text(f"[error] {row.get('content')}")])
            )
            continue

        if message_type in ("text", "reasoning", "tool_call", "mcp_call") and role == "assistant":
            if message_type in ("tool_call", "mcp_call"):
                if call_id and call_id in seen_tool_calls:
                    continue
                if call_id:
                    seen_tool_calls.add(call_id)

            content = _row_to_content(row)
            if content is not None:
                assistant_contents.append(content)
            continue

    flush_assistant()
    return messages


def _row_to_maf_message(row: dict[str, Any]) -> Message | None:
    """Single-row conversion (used by tests or legacy paths)."""
    rebuilt = to_maf_messages([row])
    return rebuilt[0] if rebuilt else None


def maf_message_to_rows(
    chat_id: str,
    message: Message,
    *,
    start_sequence: int,
    call_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Convert a MAF Message into one or more DB row dicts."""
    rows: list[dict[str, Any]] = []
    seq = start_sequence

    platform_type = (message.additional_properties or {}).get("platform_message_type")
    for content in message.contents or []:
        if getattr(content, "type", None) == "text_reasoning" or platform_type == "reasoning":
            meta = dict(getattr(content, "additional_properties", None) or {})
            protected = getattr(content, "protected_data", None)
            if protected:
                meta["protected_data"] = protected
            content_id = getattr(content, "id", None)
            if content_id:
                meta["content_id"] = content_id
            rows.append(
                {
                    "chat_id": chat_id,
                    "role": "assistant",
                    "message_type": "reasoning",
                    "content": getattr(content, "text", None) or "",
                    "metadata": meta,
                    "sequence": seq,
                }
            )
            seq += 1
            continue

        if getattr(content, "type", None) == "function_call":
            rows.append(
                {
                    "chat_id": chat_id,
                    "role": "assistant",
                    "message_type": "tool_call",
                    "content": None,
                    "metadata": {
                        "call_id": getattr(content, "call_id", None),
                        "tool_name": getattr(content, "name", None),
                        "arguments": getattr(content, "arguments", {}),
                    },
                    "sequence": seq,
                }
            )
            seq += 1
            continue

        if getattr(content, "type", None) == "function_result":
            call_id = getattr(content, "call_id", None)
            call_id_str = str(call_id) if call_id is not None else ""
            tool_name = (call_names or {}).get(call_id_str)
            rows.append(
                {
                    "chat_id": chat_id,
                    "role": "tool",
                    "message_type": "tool_result",
                    "content": getattr(content, "result", None),
                    "metadata": {
                        "call_id": call_id,
                        "tool_name": tool_name,
                        "result": getattr(content, "result", None),
                    },
                    "sequence": seq,
                }
            )
            seq += 1
            continue

        text = content.text if hasattr(content, "text") else str(content)
        rows.append(
            {
                "chat_id": chat_id,
                "role": message.role,
                "message_type": "text",
                "content": text,
                "metadata": {},
                "sequence": seq,
            }
        )
        seq += 1

    if not rows and message.role:
        rows.append(
            {
                "chat_id": chat_id,
                "role": message.role,
                "message_type": "text",
                "content": "",
                "metadata": {},
                "sequence": start_sequence,
            }
        )
    return rows
