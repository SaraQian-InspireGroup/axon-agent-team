import json
import logging
import uuid

from agent_framework import AgentSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chat
from app.db.redis_client import get_redis, is_redis_available

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 60 * 60 * 24


class SessionStore:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _redis_key(self, chat_id: uuid.UUID) -> str:
        return f"session:{chat_id}"

    async def get_session(self, chat_id: uuid.UUID) -> AgentSession | None:
        cached = await self._get_from_redis(chat_id)
        if cached is not None:
            return AgentSession.from_dict(cached)

        result = await self._db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat and chat.session_state:
            try:
                return AgentSession.from_dict(chat.session_state)
            except Exception:
                logger.exception("Invalid session_state for chat %s", chat_id)
        return None

    async def save_session(self, chat_id: uuid.UUID, session: AgentSession) -> None:
        payload = session.to_dict()
        await self._set_redis(chat_id, payload)

        result = await self._db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat is not None:
            chat.session_state = payload
            await self._db.flush()

    async def get_or_create(self, chat_id: uuid.UUID) -> AgentSession:
        existing = await self.get_session(chat_id)
        if existing is not None:
            return existing
        session = AgentSession(session_id=str(chat_id))
        await self.save_session(chat_id, session)
        return session

    async def _get_from_redis(self, chat_id: uuid.UUID) -> dict | None:
        if not is_redis_available():
            return None
        try:
            raw = await get_redis().get(self._redis_key(chat_id))
            if raw:
                return json.loads(raw)
        except Exception:
            logger.debug("Redis session read failed for %s; falling back to DB", chat_id)
        return None

    async def _set_redis(self, chat_id: uuid.UUID, payload: dict) -> None:
        if not is_redis_available():
            return
        try:
            await get_redis().set(
                self._redis_key(chat_id),
                json.dumps(payload),
                ex=SESSION_TTL_SECONDS,
            )
        except Exception:
            logger.debug("Redis session write failed for %s; DB snapshot still saved", chat_id)
