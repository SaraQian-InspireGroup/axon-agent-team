import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chat
from app.db.repositories.messages import MessageRepository
from app.memory.maf_mapping import maf_message_to_rows
from app.platform.agent_factory import AgentFactory
from app.platform.session_store import SessionStore


class ChatRunService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._messages = MessageRepository(db)
        self._sessions = SessionStore(db)
        self._factory = AgentFactory(db)

    async def _get_chat(self, chat_id: uuid.UUID) -> Chat:
        result = await self._db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat is None:
            raise ValueError(f"Chat not found: {chat_id}")
        return chat

    async def _maybe_set_chat_title(self, chat: Chat, content: str) -> None:
        if chat.title and chat.title != "New Chat":
            return
        snippet = " ".join(content.strip().split())[:60]
        if snippet:
            chat.title = snippet

    async def run_message(self, chat_id: uuid.UUID, content: str) -> str:
        chat = await self._get_chat(chat_id)
        session = await self._sessions.get_or_create(chat_id)
        bundle = await self._factory.build(chat.agent_id, chat_id=chat_id)
        await self._messages.insert(chat_id=chat_id, role="user", message_type="text", content=content)
        await self._maybe_set_chat_title(chat, content)
        async with bundle as agent:
            result = await agent.run(content, session=session)
        await self._persist_agent_messages(chat_id, result)
        await self._sessions.save_session(chat_id, session)
        await self._db.commit()
        return result.text or ""

    async def stream_message(self, chat_id: uuid.UUID, content: str) -> AsyncIterator[dict[str, Any]]:
        chat = await self._get_chat(chat_id)
        session = await self._sessions.get_or_create(chat_id)
        bundle = await self._factory.build(chat.agent_id, chat_id=chat_id)
        await self._messages.insert(chat_id=chat_id, role="user", message_type="text", content=content)
        await self._maybe_set_chat_title(chat, content)
        async with bundle as agent:
            emitter = _StreamSseEmitter(chat_id)
            stream = agent.run(content, session=session, stream=True)
            async for update in stream:
                for event in emitter.emit(update):
                    yield event
            for event in emitter.flush():
                yield event
            final = await stream.get_final_response()
        await self._persist_agent_messages(chat_id, final)
        await self._sessions.save_session(chat_id, session)
        await self._db.commit()
        yield {"event": "done", "data": {"text": final.text or ""}}

    async def _persist_agent_messages(self, chat_id: uuid.UUID, response: Any) -> None:
        saved = 0
        call_names = _collect_call_names(getattr(response, "messages", None) or [])
        for message in getattr(response, "messages", None) or []:
            next_seq = await self._messages.next_sequence(chat_id)
            for row in maf_message_to_rows(
                str(chat_id),
                message,
                start_sequence=next_seq,
                call_names=call_names,
            ):
                await self._messages.insert(
                    chat_id=chat_id,
                    role=row["role"],
                    message_type=row["message_type"],
                    content=row.get("content"),
                    metadata=row.get("metadata"),
                    sequence=row["sequence"],
                )
                saved += 1
        text = getattr(response, "text", None)
        if text and saved == 0:
            await self._messages.insert(
                chat_id=chat_id,
                role="assistant",
                message_type="text",
                content=text,
            )
        await self._db.flush()

def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def _collect_call_names(messages: list[Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for message in messages:
        for content in getattr(message, "contents", None) or []:
            if getattr(content, "type", None) != "function_call":
                continue
            call_id = getattr(content, "call_id", None)
            tool_name = getattr(content, "name", None)
            if call_id is not None and tool_name:
                names[str(call_id)] = str(tool_name)
    return names


class _StreamSseEmitter:
    """Convert MAF stream updates into SSE events for the chat UI."""

    def __init__(self, chat_id: uuid.UUID) -> None:
        self._chat_id = chat_id
        self._emitted_calls: set[str] = set()
        self._emitted_results: set[str] = set()
        self._call_names: dict[str, str] = {}
        self._reasoning_open = False

    def _close_reasoning(self, chat_id: str) -> dict[str, Any] | None:
        if not self._reasoning_open:
            return None
        self._reasoning_open = False
        return {"event": "reasoning_done", "data": {"chat_id": chat_id}}

    def emit(self, update: Any) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        chat_id = str(self._chat_id)

        for content in getattr(update, "contents", None) or []:
            content_type = getattr(content, "type", None)

            if content_type == "text_reasoning":
                text = getattr(content, "text", None)
                if text:
                    self._reasoning_open = True
                    events.append(
                        {
                            "event": "reasoning",
                            "data": {"chat_id": chat_id, "text": text},
                        }
                    )
                continue

            if content_type in ("function_call", "function_result", "text"):
                done = self._close_reasoning(chat_id)
                if done:
                    events.append(done)

            if content_type == "function_call":
                call_id = str(getattr(content, "call_id", "") or "")
                tool_name = str(getattr(content, "name", "") or "").strip()
                if not call_id or not tool_name or call_id in self._emitted_calls:
                    continue
                self._emitted_calls.add(call_id)
                self._call_names[call_id] = tool_name
                events.append(
                    {
                        "event": "tool_call",
                        "data": {
                            "chat_id": chat_id,
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "arguments": _json_safe(getattr(content, "arguments", {})),
                        },
                    }
                )
                continue

            if content_type == "function_result":
                call_id = str(getattr(content, "call_id", "") or "")
                if not call_id or call_id in self._emitted_results:
                    continue
                self._emitted_results.add(call_id)
                events.append(
                    {
                        "event": "tool_result",
                        "data": {
                            "chat_id": chat_id,
                            "call_id": call_id,
                            "tool_name": self._call_names.get(call_id, ""),
                            "result": _json_safe(getattr(content, "result", None)),
                        },
                    }
                )
                continue

            if content_type == "text":
                text = getattr(content, "text", None)
                if text:
                    events.append(
                        {
                            "event": "text",
                            "data": {"chat_id": chat_id, "text": text},
                        }
                    )
            elif isinstance(content, str) and content:
                done = self._close_reasoning(chat_id)
                if done:
                    events.append(done)
                events.append(
                    {
                        "event": "text",
                        "data": {"chat_id": chat_id, "text": content},
                    }
                )

        return events

    def flush(self) -> list[dict[str, Any]]:
        done = self._close_reasoning(str(self._chat_id))
        return [done] if done else []


async def list_chat_messages(db: AsyncSession, chat_id: uuid.UUID) -> list[dict[str, Any]]:
    repo = MessageRepository(db)
    rows = await repo.list_by_chat(chat_id)
    return [
        {
            "id": str(r.id),
            "chat_id": str(r.chat_id),
            "role": r.role,
            "message_type": r.message_type,
            "content": r.content,
            "metadata": r.message_metadata,
            "parent_id": str(r.parent_id) if r.parent_id else None,
            "sequence": r.sequence,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
