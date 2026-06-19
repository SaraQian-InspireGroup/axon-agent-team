import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ChatCreate, ChatListOut, ChatOut, MessageCreate, MessageOut, ProposalDraftOut, ProposalPreviewOut
from app.db.models import AgentModel, Chat
from app.platform.current_user import get_current_user_id
from app.db.session import get_db
from app.services.chat_run import ChatRunService, list_chat_messages
from app.services.proposal_preview_service import get_chat_proposal_draft, get_chat_proposal_preview
from app.proposal.storage import artifact_download_filename, resolve_artifact_path

router = APIRouter(prefix="/chats", tags=["chats"])


def _chat_list_out(chat: Chat) -> ChatListOut:
    return ChatListOut(
        id=chat.id,
        agent_id=chat.agent_id,
        title=chat.title,
        created_at=chat.created_at.isoformat() if chat.created_at else None,
        updated_at=chat.updated_at.isoformat() if chat.updated_at else None,
    )


@router.get("", response_model=list[ChatListOut])
async def list_chats(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ChatListOut]:
    result = await db.execute(
        select(Chat)
        .where(
            Chat.user_id == get_current_user_id(),
            Chat.agent_id == agent_id,
        )
        .order_by(Chat.updated_at.desc())
        .limit(50)
    )
    return [_chat_list_out(c) for c in result.scalars().all()]


@router.post("", response_model=ChatOut, status_code=201)
async def create_chat(body: ChatCreate, db: AsyncSession = Depends(get_db)) -> ChatOut:
    agent = await db.get(AgentModel, body.agent_id)
    if agent is None or agent.slug is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    chat = Chat(
        user_id=get_current_user_id(),
        agent_id=body.agent_id,
        title=body.title or "New Chat",
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return ChatOut(id=chat.id, user_id=chat.user_id, agent_id=chat.agent_id, title=chat.title)


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[MessageOut]:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    rows = await list_chat_messages(db, chat_id)
    return [MessageOut(**row) for row in rows]


@router.get("/{chat_id}/proposal/preview", response_model=ProposalPreviewOut)
async def get_proposal_preview(
    chat_id: uuid.UUID,
    draft: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ProposalPreviewOut:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    try:
        payload = await get_chat_proposal_preview(db, chat_id, draft=draft)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProposalPreviewOut(**payload)


@router.get("/{chat_id}/proposal/draft", response_model=ProposalDraftOut)
async def get_proposal_draft(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProposalDraftOut:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    try:
        payload = await get_chat_proposal_draft(db, chat_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProposalDraftOut(**payload)


@router.get("/{chat_id}/artifacts/{artifact_id}")
async def download_artifact(
    chat_id: uuid.UUID,
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    path = resolve_artifact_path(chat_id, artifact_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    filename = artifact_download_filename(chat_id, artifact_id)
    return FileResponse(
        path,
        media_type="text/markdown; charset=utf-8",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{chat_id}/messages")
async def post_message(
    chat_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    service = ChatRunService(db)
    try:
        text = await service.run_message(chat_id, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"chat_id": str(chat_id), "text": text}


@router.post("/{chat_id}/stream")
async def stream_message(
    chat_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    service = ChatRunService(db)

    def _stream_error_message(exc: Exception) -> str:
        name = type(exc).__name__
        text = str(exc)
        if "AuthenticationError" in name or "401" in text or "Unauthorized" in text:
            return (
                "Claude 模型认证失败（401）：请检查 backend/.env 中的 "
                "CLAUDE_AZURE_API_KEY 与 CLAUDE_AZURE_FOUNDRY_ENDPOINT 是否与 Azure 资源区域一致。"
            )
        return text or name

    async def event_generator():
        try:
            async for event in service.stream_message(chat_id, body.content):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except ValueError as exc:
            payload = {"error": str(exc)}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            payload = {"error": _stream_error_message(exc)}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
