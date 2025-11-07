from pydantic import BaseModel, Field
from typing import Optional, List

class ChatMessage(BaseModel):
    content: str
    role: str = Field(default="user", pattern="^(user|assistant|system)$")
    name: str | None = Field(default=None, description="User's name")

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)

class ChatResponse(BaseModel):
    response: str



