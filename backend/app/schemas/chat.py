from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    conversation_id: UUID
