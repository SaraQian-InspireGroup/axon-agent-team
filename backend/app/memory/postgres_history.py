import uuid
from collections.abc import Sequence

from agent_framework import HistoryProvider, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.messages import MessageRepository
from app.memory.maf_mapping import maf_message_to_rows, row_to_dict, to_maf_messages


class PostgresHistoryProvider(HistoryProvider):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            "postgres-history",
            load_messages=True,
            store_inputs=False,
            store_outputs=False,
        )
        self._session = session
        self._repo = MessageRepository(session)

    async def get_messages(
        self, session_id: str | None, *, state: dict | None = None, **kwargs
    ) -> list[Message]:
        if not session_id:
            return []
        chat_id = uuid.UUID(session_id)
        rows = await self._repo.list_by_chat(chat_id)
        return to_maf_messages([row_to_dict(r) for r in rows])

    async def save_messages(
        self,
        session_id: str | None,
        messages: Sequence[Message],
        *,
        state: dict | None = None,
        **kwargs,
    ) -> None:
        if not session_id or not messages:
            return
        chat_id = uuid.UUID(session_id)
        next_seq = await self._repo.next_sequence(chat_id)
        for message in messages:
            for row in maf_message_to_rows(session_id, message, start_sequence=next_seq):
                await self._repo.insert(
                    chat_id=chat_id,
                    role=row["role"],
                    message_type=row["message_type"],
                    content=row.get("content"),
                    metadata=row.get("metadata"),
                    sequence=row["sequence"],
                )
                next_seq = row["sequence"] + 1
        if state is not None:
            state.setdefault(self.source_id, {})["history_key"] = session_id
        await self._session.flush()
