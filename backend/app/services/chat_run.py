import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from agent_framework import MiddlewareTermination
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentModel, Chat, Message
from app.db.repositories.messages import MessageRepository
from app.memory.long_term import try_handle_memory_command
from app.memory.maf_mapping import maf_message_to_rows
from app.memory.memory_config import MemoryConfig, parse_memory_config
from app.platform.agent_factory import AgentFactory
from app.platform.platform_instructions import RUN_CANCELLED_USER_TEXT
from app.platform.session_store import SessionStore
from app.runs.manager import get_run_manager

logger = logging.getLogger(__name__)

_TOOL_ROW_TYPES = frozenset({"tool_call", "tool_result", "mcp_call", "mcp_result"})


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

    async def _commit_user_turn(self, chat: Chat, content: str) -> Message:
        """Persist the user message immediately so it survives agent failures."""
        row = await self._messages.insert(
            chat_id=chat.id, role="user", message_type="text", content=content
        )
        await self._maybe_set_chat_title(chat, content)
        await self._db.commit()
        return row

    async def _finalize_cancel(
        self,
        chat_id: uuid.UUID,
        run_id: uuid.UUID,
        accumulator: "_StreamTurnAccumulator",
    ) -> None:
        """Persist partial assistant output and a user-visible cancellation marker."""
        try:
            if accumulator.has_content():
                await accumulator.persist_cancelled(self._messages, chat_id, run_id)
            await self._messages.insert(
                chat_id=chat_id,
                role="user",
                message_type="run_cancelled",
                content=RUN_CANCELLED_USER_TEXT,
                metadata={"run_id": str(run_id), "cancelled_by": "user"},
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to persist cancelled turn for chat %s", chat_id)
            await self._db.rollback()

    async def _memory_config_for_chat(self, chat: Chat) -> MemoryConfig:
        agent = await self._db.get(AgentModel, chat.agent_id)
        return parse_memory_config(agent.config if agent else {})

    async def _finalize_success(
        self,
        chat_id: uuid.UUID,
        session: Any,
        response: Any,
        *,
        memory_config: MemoryConfig,
        turn_start_sequence: int,
        accumulator: "_StreamTurnAccumulator | None" = None,
    ) -> None:
        if accumulator is not None and accumulator.has_content():
            await accumulator.persist(self._messages, chat_id)
        else:
            await self._persist_agent_messages(chat_id, response, skip_tool_rows=False)
        await self._sessions.append_completed_turn(
            chat_id,
            memory_config,
            turn_start_sequence=turn_start_sequence,
        )
        await self._sessions.save_session(chat_id, session)
        await self._db.commit()

    async def _finalize_failure(
        self,
        chat_id: uuid.UUID,
        exc: Exception,
        *,
        response: Any | None = None,
        accumulator: "_StreamTurnAccumulator | None" = None,
    ) -> None:
        """Best-effort persist of partial assistant output plus an error row."""
        try:
            if response is not None:
                await self._persist_agent_messages(chat_id, response)
            elif accumulator is not None and accumulator.has_content():
                await accumulator.persist(self._messages, chat_id)
            await self._persist_run_error(chat_id, exc)
            await self._db.commit()
        except Exception:
            logger.exception("Failed to persist partial turn for chat %s", chat_id)
            await self._db.rollback()

    async def _persist_run_error(self, chat_id: uuid.UUID, exc: Exception) -> None:
        message = str(exc).strip() or type(exc).__name__
        await self._messages.insert(
            chat_id=chat_id,
            role="assistant",
            message_type="error",
            content=message[:4000],
            metadata={"error_type": type(exc).__name__},
        )
        await self._db.flush()

    async def run_message(self, chat_id: uuid.UUID, content: str) -> str:
        chat = await self._get_chat(chat_id)
        memory_config = await self._memory_config_for_chat(chat)
        session = await self._sessions.get_or_create(chat_id)
        user_row = await self._commit_user_turn(chat, content)
        memory_result = await try_handle_memory_command(
            self._db,
            user_id=chat.user_id,
            agent_id=chat.agent_id,
            content=content,
        )
        if memory_result and memory_result.handled:
            if memory_result.is_pure_command:
                await self._messages.insert(
                    chat_id=chat_id,
                    role="assistant",
                    message_type="text",
                    content=memory_result.confirmation,
                    metadata={"source": "memory_command"},
                )
            await self._db.commit()
            if memory_result.is_pure_command:
                return memory_result.confirmation

        bundle = await self._factory.build(
            chat.agent_id,
            chat_id=chat_id,
            user_id=chat.user_id,
            turn_start_sequence=user_row.sequence,
            session_store=self._sessions,
        )
        try:
            async with bundle as agent:
                result = await agent.run(content, session=session)
            await self._finalize_success(
                chat_id,
                session,
                result,
                memory_config=memory_config,
                turn_start_sequence=user_row.sequence,
            )
            return result.text or ""
        except Exception as exc:
            await self._finalize_failure(chat_id, exc)
            raise

    async def stream_message(self, chat_id: uuid.UUID, content: str) -> AsyncIterator[dict[str, Any]]:
        chat = await self._get_chat(chat_id)
        memory_config = await self._memory_config_for_chat(chat)
        session = await self._sessions.get_or_create(chat_id)
        user_row = await self._commit_user_turn(chat, content)
        memory_result = await try_handle_memory_command(
            self._db,
            user_id=chat.user_id,
            agent_id=chat.agent_id,
            content=content,
        )
        if memory_result and memory_result.handled:
            if memory_result.is_pure_command:
                await self._messages.insert(
                    chat_id=chat_id,
                    role="assistant",
                    message_type="text",
                    content=memory_result.confirmation,
                    metadata={"source": "memory_command"},
                )
            await self._db.commit()
            yield {
                "event": "memory_updated",
                "data": memory_result.to_dict(),
            }
            if memory_result.is_pure_command:
                yield {"event": "done", "data": {"text": memory_result.confirmation}}
                return

        run_manager = get_run_manager()
        run = await run_manager.start_run(chat_id, user_row.id)

        emitter = _StreamSseEmitter(chat_id)
        accumulator = _StreamTurnAccumulator()

        async def finalize_cancel_once() -> None:
            await self._finalize_cancel(chat_id, run.run_id, accumulator)

        await run_manager.register_finalize(run.run_id, finalize_cancel_once)
        yield {
            "event": "run_started",
            "data": {
                "run_id": str(run.run_id),
                "chat_id": str(chat_id),
                "user_message_id": str(user_row.id),
            },
        }

        final: Any | None = None

        async def _emit_cancelled() -> AsyncIterator[dict[str, Any]]:
            await run_manager.finalize_cancelled(run.run_id)
            yield {
                "event": "run_cancelled",
                "data": {"run_id": str(run.run_id), "chat_id": str(chat_id)},
            }

        try:
            bundle = await self._factory.build(
                chat.agent_id,
                chat_id=chat_id,
                user_id=chat.user_id,
                stop_event=run.stop_event,
                turn_start_sequence=user_row.sequence,
                session_store=self._sessions,
            )
            async with bundle as agent:
                stream = agent.run(content, session=session, stream=True)
                async for update in stream:
                    if run.stop_event.is_set():
                        break
                    accumulator.observe(update)
                    for event in emitter.emit(update):
                        yield event

                for event in emitter.flush():
                    yield event

                if run.stop_event.is_set():
                    async for event in _emit_cancelled():
                        yield event
                    return

                final = await stream.get_final_response()

            await self._finalize_success(
                chat_id,
                session,
                final,
                memory_config=memory_config,
                turn_start_sequence=user_row.sequence,
                accumulator=accumulator,
            )
            yield {"event": "done", "data": {"text": final.text or ""}}
        except MiddlewareTermination:
            if run.stop_event.is_set():
                async for event in _emit_cancelled():
                    yield event
                return
            raise
        except asyncio.CancelledError:
            if run.stop_event.is_set():
                async for event in _emit_cancelled():
                    yield event
                return
            raise
        except Exception as exc:
            if run.stop_event.is_set():
                async for event in _emit_cancelled():
                    yield event
                return
            await self._finalize_failure(chat_id, exc, response=final, accumulator=accumulator)
            raise
        finally:
            await run_manager.complete(run.run_id)

    async def _persist_agent_messages(
        self,
        chat_id: uuid.UUID,
        response: Any,
        *,
        skip_tool_rows: bool = False,
    ) -> None:
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
                if skip_tool_rows and row["message_type"] in _TOOL_ROW_TYPES:
                    continue
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


def _normalize_tool_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return _json_safe(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return _json_safe(parsed)
        except json.JSONDecodeError:
            return {"raw": stripped}
    return {"raw": str(raw)}


def _tool_arguments_richness(arguments: dict[str, Any]) -> int:
    if not arguments:
        return 0
    try:
        return len(json.dumps(arguments, ensure_ascii=False, default=str))
    except TypeError:
        return len(str(arguments))


def _merge_tool_arguments(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, Any]:
    left = existing or {}
    right = incoming or {}
    if _tool_arguments_richness(right) >= _tool_arguments_richness(left):
        return right
    return left


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


class _StreamTurnAccumulator:
    """Tracks streamed assistant output for persistence when a run fails mid-turn."""

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []
        self._reasoning_buffer = ""
        self._text_buffer = ""
        self._emitted_calls: set[str] = set()
        self._emitted_results: set[str] = set()
        self._call_names: dict[str, str] = {}

    def observe(self, update: Any) -> None:
        for content in getattr(update, "contents", None) or []:
            self._observe_content(content)

    def _flush_reasoning(self) -> None:
        if not self._reasoning_buffer:
            return
        self._rows.append(
            {
                "role": "assistant",
                "message_type": "reasoning",
                "content": self._reasoning_buffer,
                "metadata": {},
            }
        )
        self._reasoning_buffer = ""

    def _flush_text(self) -> None:
        if not self._text_buffer:
            return
        self._rows.append(
            {
                "role": "assistant",
                "message_type": "text",
                "content": self._text_buffer,
                "metadata": {},
            }
        )
        self._text_buffer = ""

    def _append_text(self, chunk: str) -> None:
        if not self._text_buffer:
            self._text_buffer = chunk
            return
        if chunk.startswith(self._text_buffer):
            self._text_buffer = chunk
            return
        if self._text_buffer.startswith(chunk):
            return
        self._text_buffer += chunk

    def _observe_content(self, content: Any) -> None:
        content_type = getattr(content, "type", None)

        if content_type == "text_reasoning":
            text = getattr(content, "text", None)
            if text:
                self._reasoning_buffer += text
            return

        if content_type in ("function_call", "function_result", "text"):
            self._flush_reasoning()

        if content_type == "function_call":
            call_id = str(getattr(content, "call_id", "") or "")
            tool_name = str(getattr(content, "name", "") or "").strip()
            if not call_id or not tool_name:
                return
            arguments = _normalize_tool_arguments(getattr(content, "arguments", {}))
            self._call_names[call_id] = tool_name
            self._flush_text()
            if call_id in self._emitted_calls:
                for row in reversed(self._rows):
                    if row.get("message_type") != "tool_call":
                        continue
                    meta = row.get("metadata") or {}
                    if str(meta.get("call_id") or "") != call_id:
                        continue
                    meta["arguments"] = _merge_tool_arguments(meta.get("arguments"), arguments)
                    row["metadata"] = meta
                    break
                return
            self._emitted_calls.add(call_id)
            self._rows.append(
                {
                    "role": "assistant",
                    "message_type": "tool_call",
                    "content": None,
                    "metadata": {
                        "call_id": call_id,
                        "tool_name": tool_name,
                        "arguments": arguments,
                    },
                }
            )
            return

        if content_type == "function_result":
            call_id = str(getattr(content, "call_id", "") or "")
            if not call_id or call_id in self._emitted_results:
                return
            self._emitted_results.add(call_id)
            result = _json_safe(getattr(content, "result", None))
            content_value = result if isinstance(result, str) else None
            self._rows.append(
                {
                    "role": "tool",
                    "message_type": "tool_result",
                    "content": content_value,
                    "metadata": {
                        "call_id": call_id,
                        "tool_name": self._call_names.get(call_id, ""),
                        "result": result,
                    },
                }
            )
            return

        if content_type == "text":
            text = getattr(content, "text", None)
            if text:
                self._append_text(text)
            return

        if isinstance(content, str) and content:
            self._append_text(content)

    def finalize(self) -> None:
        self._flush_reasoning()
        self._flush_text()

    def has_content(self) -> bool:
        return bool(self._rows or self._reasoning_buffer or self._text_buffer)

    def has_tool_rows(self) -> bool:
        return any(row.get("message_type") in _TOOL_ROW_TYPES for row in self._rows)

    async def persist_tool_rows(self, repo: MessageRepository, chat_id: uuid.UUID) -> int:
        """Persist tool call/result rows captured during streaming (with full arguments)."""
        self.finalize()
        saved = 0
        for row in self._rows:
            if row.get("message_type") not in _TOOL_ROW_TYPES:
                continue
            await repo.insert(
                chat_id=chat_id,
                role=row["role"],
                message_type=row["message_type"],
                content=row.get("content"),
                metadata=row.get("metadata") or {},
            )
            saved += 1
        return saved

    async def persist(self, repo: MessageRepository, chat_id: uuid.UUID) -> int:
        self.finalize()
        saved = 0
        for row in self._rows:
            await repo.insert(chat_id=chat_id, **row)
            saved += 1
        return saved

    async def persist_cancelled(
        self,
        repo: MessageRepository,
        chat_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> int:
        """Write partial turn output; incomplete assistant text/reasoning marked cancelled."""
        self.finalize()
        run_meta = {"run_id": str(run_id)}
        saved = 0
        for row in self._rows:
            message_type = row["message_type"]
            meta = {**(row.get("metadata") or {}), **run_meta}
            if message_type in ("tool_call", "tool_result"):
                await repo.insert(
                    chat_id=chat_id,
                    role=row["role"],
                    message_type=message_type,
                    content=row.get("content"),
                    metadata=meta,
                )
                saved += 1
                continue
            if message_type in ("reasoning", "text"):
                await repo.insert(
                    chat_id=chat_id,
                    role="assistant",
                    message_type="cancelled",
                    content=row.get("content"),
                    metadata={
                        **meta,
                        "partial": True,
                        "original_type": message_type,
                    },
                )
                saved += 1
        return saved


class _StreamSseEmitter:
    """Convert MAF stream updates into SSE events for the chat UI."""

    def __init__(self, chat_id: uuid.UUID) -> None:
        self._chat_id = chat_id
        self._emitted_calls: set[str] = set()
        self._emitted_results: set[str] = set()
        self._call_names: dict[str, str] = {}
        self._call_arguments: dict[str, dict[str, Any]] = {}
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
                if not call_id or not tool_name:
                    continue
                arguments = _normalize_tool_arguments(getattr(content, "arguments", {}))
                self._call_names[call_id] = tool_name
                merged = _merge_tool_arguments(self._call_arguments.get(call_id), arguments)
                self._call_arguments[call_id] = merged
                self._emitted_calls.add(call_id)
                events.append(
                    {
                        "event": "tool_call",
                        "data": {
                            "chat_id": chat_id,
                            "call_id": call_id,
                            "tool_name": tool_name,
                            "arguments": merged,
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
