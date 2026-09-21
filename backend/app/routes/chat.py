from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Conversation, Message, User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import ai_service

router = APIRouter(tags=["Chat"])


def _conversation_title(message: str) -> str:
    compact = " ".join(message.split())
    if len(compact) <= 80:
        return compact or "New conversation"
    return f"{compact[:77].rstrip()}..."


async def _get_or_create_conversation(
    db: AsyncSession,
    user: User,
    conversation_id: UUID | None,
    title_source: str,
) -> tuple[Conversation, list[Message]]:
    if conversation_id is not None:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation, list(conversation.messages)

    conversation = Conversation(
        user_id=user.id,
        title=_conversation_title(title_source),
    )
    db.add(conversation)
    await db.flush()
    return conversation, []


@router.post("/api/chat", response_model=ChatResponse)
@router.post("/api/chat/", response_model=ChatResponse)
@router.post("/chat", response_model=ChatResponse)
@router.post("/chat/", response_model=ChatResponse)
async def send_chat_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    conversation, stored_messages = await _get_or_create_conversation(
        db,
        current_user,
        payload.conversation_id,
        user_message,
    )

    history = payload.history
    if stored_messages:
        history = [
            {"role": item.role, "content": item.content}
            for item in stored_messages
        ]

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=user_message,
        )
    )

    try:
        content = await ai_service.generate_chat_response(user_message, history)
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=content,
        )
    )
    await db.commit()

    return ChatResponse(
        role="assistant",
        content=content,
        conversation_id=conversation.id,
    )
