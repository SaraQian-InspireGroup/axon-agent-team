import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AttachmentOut,
    ChatCreate,
    ChatListOut,
    ChatOut,
    MessageCreate,
    MessageOut,
    ProposalDraftOut,
    ProposalExportOut,
    ProposalExportRequest,
    ProposalPreviewOut,
)
from app.db.models import AgentModel, Chat
from app.platform.current_user import get_current_user_id
from app.db.session import get_db
from app.services.attachment_service import AttachmentService
from app.services.chat_run import ChatRunService, list_chat_messages
from app.services.stream_errors import user_facing_stream_error
from app.services.proposal_preview_service import get_chat_proposal_draft, get_chat_proposal_preview, load_chat_proposal_draft
from app.proposal.export_service import ProposalExportError, generate_proposal_docx
from app.proposal.storage import artifact_download_filename, artifact_media_type, resolve_artifact_path

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


@router.post("/{chat_id}/proposal/export", response_model=ProposalExportOut)
async def export_proposal(
    chat_id: uuid.UUID,
    body: ProposalExportRequest,
    db: AsyncSession = Depends(get_db),
) -> ProposalExportOut:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if body.format != "docx":
        raise HTTPException(status_code=422, detail="Only format=docx is supported.")
    try:
        draft = await load_chat_proposal_draft(db, chat_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not draft:
        raise HTTPException(status_code=422, detail="Proposal draft is not initialized.")
    try:
        payload = generate_proposal_docx(draft, chat_id=chat_id, force=body.force, persist=True)
    except ProposalExportError as exc:
        detail: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.code == "blocked":
            from app.proposal.draft import build_draft_preview

            preview = build_draft_preview(draft)
            detail["missing_required"] = (preview.get("completeness") or {}).get("missing_required") or []
        raise HTTPException(status_code=exc.http_status, detail=detail) from exc
    return ProposalExportOut(**payload)


@router.get("/{chat_id}/artifacts/{artifact_id}")
async def download_artifact(
    chat_id: uuid.UUID,
    artifact_id: str,
    format: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    variant = format.strip().lower() if format else None
    path = resolve_artifact_path(chat_id, artifact_id, variant=variant)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    filename = artifact_download_filename(chat_id, artifact_id, variant=variant)
    return FileResponse(
        path,
        media_type=artifact_media_type(chat_id, artifact_id, variant=variant),
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{chat_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    chat_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    service = AttachmentService(db)
    try:
        payload = await service.upload(
            chat_id,
            filename=file.filename,
            mime_type=mime_type,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"File upload failed: {exc}") from exc

    return AttachmentOut(
        id=uuid.UUID(payload["id"]),
        chat_id=chat_id,
        filename=payload["filename"],
        mime_type=payload["mime_type"],
        size_bytes=payload["size_bytes"],
        provider=payload["provider"],
        provider_file_id=payload["provider_file_id"],
        created_at=None,
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
        text = await service.run_message(
            chat_id,
            body.content,
            attachment_ids=body.attachment_ids,
        )
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
        return user_facing_stream_error(exc)

    async def event_generator():
        try:
            async for event in service.stream_message(
                chat_id,
                body.content,
                attachment_ids=body.attachment_ids,
            ):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except ValueError as exc:
            payload = {"error": str(exc)}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            payload = {"error": _stream_error_message(exc)}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
