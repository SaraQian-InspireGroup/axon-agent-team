import uuid
from typing import Any

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    name: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None = None


class AgentOut(BaseModel):
    id: uuid.UUID
    slug: str | None = None
    name: str
    description: str | None
    model_provider: str
    model_name: str


class ChatCreate(BaseModel):
    agent_id: uuid.UUID
    user_id: uuid.UUID | None = None
    title: str | None = None


class ChatOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None


class ChatListOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None
    created_at: str | None
    updated_at: str | None


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: str
    chat_id: str
    role: str
    message_type: str
    content: str | None
    metadata: dict[str, Any]
    parent_id: str | None
    sequence: int
    created_at: str | None


class MemoryBulletOut(BaseModel):
    prefix: str
    text: str
    line: str
    kind: str


class MemoryOut(BaseModel):
    scope: str
    agent_id: uuid.UUID | None = None
    content: str
    revision: int
    bullets: list[MemoryBulletOut] = Field(default_factory=list)
    updated_at: str | None = None


class MemoryReplaceIn(BaseModel):
    content: str = ""


class MemoryAppendIn(BaseModel):
    scope: str
    agent_id: uuid.UUID | None = None
    lines: list[str]
    is_constraint: bool = False
    source: str = "ui"


class MemoryRemoveIn(BaseModel):
    scope: str
    agent_id: uuid.UUID | None = None
    match: str
    also_search_user: bool = False
