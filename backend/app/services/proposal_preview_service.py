"""Load persisted proposal state and build live preview responses."""

from __future__ import annotations

import copy
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentModel, Chat
from app.db.repositories.messages import MessageRepository
from app.platform.session_store import SessionStore
from app.proposal.preview import build_live_preview
from app.proposal.recover import recover_proposal_state_from_messages
from app.proposal.rehydrate import rehydrate_proposal_state
from app.proposal.state import empty_proposal_state
from app.proposal.store import load_proposal_state_from_payload

PROPOSAL_AGENT_SLUG = "proposal-composer"


async def get_chat_proposal_preview(
    db: AsyncSession,
    chat_id: uuid.UUID,
    *,
    draft: bool = True,
) -> dict:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise ValueError(f"Chat not found: {chat_id}")

    agent = await db.get(AgentModel, chat.agent_id)
    if agent is None or agent.slug != PROPOSAL_AGENT_SLUG:
        raise ValueError("Proposal preview is only available for Proposal Composer chats.")

    store = SessionStore(db)
    messages = MessageRepository(db)
    payload = await store.get_payload(chat_id)
    stored = load_proposal_state_from_payload(payload)
    if stored is None:
        db_payload = await store._load_payload_from_db(chat_id)
        stored = load_proposal_state_from_payload(db_payload)
    if stored is None:
        stored = await recover_proposal_state_from_messages(messages, chat_id)
    state = empty_proposal_state() if stored is None else copy.deepcopy(stored)
    if stored is not None:
        rehydrate_proposal_state(state)
    preview = build_live_preview(state, draft=draft)
    preview["chat_id"] = str(chat_id)
    return preview
