from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict



class ChatMessage(BaseModel):
    content: str
    role: str = Field(default="user", pattern="^(user|assistant|system)$")
    name: str | None = Field(default=None, description="User's name")

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)

class ChatResponse(BaseModel):
    response: str

class ChatQuery(BaseModel):
    query: str

class AgentPayload(BaseModel):
    content: str
    categories: List[str]
    analysis: Dict
    timestamp: str
    source: str

class EmailRequest(BaseModel):
    recipient: EmailStr
    subject: str
    body: str