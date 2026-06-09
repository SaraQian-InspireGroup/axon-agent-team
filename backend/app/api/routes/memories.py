import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MemoryAppendIn, MemoryOut, MemoryRemoveIn, MemoryReplaceIn
from app.db.session import get_db
from app.memory.long_term.formatter import parse_bullets, validate_line
from app.memory.long_term.repository import MemoryRepository, MemoryScope
from app.platform.current_user import get_current_user_id

router = APIRouter(prefix="/memories", tags=["memories"])


def _to_out(snapshot) -> MemoryOut:
    bullets = []
    for prefix, text in parse_bullets(snapshot.content):
        bullets.append(
            {
                "prefix": prefix,
                "text": text,
                "line": f"[!] {text}" if prefix == "[!]" else f"- {text}",
                "kind": "constraint" if prefix == "[!]" else "bullet",
            }
        )
    return MemoryOut(
        scope=snapshot.scope,
        agent_id=snapshot.agent_id,
        content=snapshot.content,
        revision=snapshot.revision,
        bullets=bullets,
        updated_at=snapshot.updated_at.isoformat() if snapshot.updated_at else None,
    )


@router.get("/user", response_model=MemoryOut)
async def get_user_memory(db: AsyncSession = Depends(get_db)) -> MemoryOut:
    user_id = get_current_user_id()
    repo = MemoryRepository(db)
    snapshot = await repo.get_or_create_snapshot(user_id, MemoryScope("user"))
    await db.commit()
    return _to_out(snapshot)


@router.get("/agents/{agent_id}", response_model=MemoryOut)
async def get_agent_memory(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> MemoryOut:
    user_id = get_current_user_id()
    repo = MemoryRepository(db)
    snapshot = await repo.get_or_create_snapshot(user_id, MemoryScope("agent", agent_id=agent_id))
    await db.commit()
    return _to_out(snapshot)


@router.put("/user", response_model=MemoryOut)
async def replace_user_memory(body: MemoryReplaceIn, db: AsyncSession = Depends(get_db)) -> MemoryOut:
    user_id = get_current_user_id()
    repo = MemoryRepository(db)
    snapshot = await repo.replace_content(user_id, MemoryScope("user"), body.content, source="ui")
    await db.commit()
    return _to_out(snapshot)


@router.put("/agents/{agent_id}", response_model=MemoryOut)
async def replace_agent_memory(
    agent_id: uuid.UUID,
    body: MemoryReplaceIn,
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    user_id = get_current_user_id()
    repo = MemoryRepository(db)
    snapshot = await repo.replace_content(
        user_id,
        MemoryScope("agent", agent_id=agent_id),
        body.content,
        source="ui",
    )
    await db.commit()
    return _to_out(snapshot)


@router.post("/append", response_model=MemoryOut)
async def append_memory(body: MemoryAppendIn, db: AsyncSession = Depends(get_db)) -> MemoryOut:
    user_id = get_current_user_id()
    if body.scope == "agent" and body.agent_id is None:
        raise HTTPException(status_code=400, detail="agent_id required for agent scope")
    if body.scope == "user" and body.agent_id is not None:
        raise HTTPException(status_code=400, detail="agent_id must be null for user scope")

    lines = []
    for raw in body.lines:
        if body.is_constraint or raw.strip().startswith("[!]"):
            text = raw.strip().removeprefix("[!]").strip()
            lines.append(validate_line(f"[!] {text}"))
        else:
            lines.append(validate_line(raw))

    memory_scope = MemoryScope(
        body.scope,
        agent_id=body.agent_id if body.scope == "agent" else None,
    )
    repo = MemoryRepository(db)
    snapshot, _ = await repo.append_lines(user_id, memory_scope, lines, source=body.source)
    await db.commit()
    return _to_out(snapshot)


@router.post("/remove", response_model=MemoryOut)
async def remove_memory(body: MemoryRemoveIn, db: AsyncSession = Depends(get_db)) -> MemoryOut:
    user_id = get_current_user_id()
    if body.scope == "agent" and body.agent_id is None:
        raise HTTPException(status_code=400, detail="agent_id required for agent scope")

    repo = MemoryRepository(db)
    if body.scope == "agent":
        memory_scope = MemoryScope("agent", agent_id=body.agent_id)
        await repo.remove_lines(
            user_id,
            memory_scope,
            match=body.match,
            also_search_user_scope=body.also_search_user,
        )
        snapshot = await repo.get_or_create_snapshot(user_id, memory_scope)
    else:
        memory_scope = MemoryScope("user")
        await repo.remove_lines(user_id, memory_scope, match=body.match)
        snapshot = await repo.get_or_create_snapshot(user_id, memory_scope)

    await db.commit()
    return _to_out(snapshot)
