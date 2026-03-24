from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None

class ChatResponse(BaseModel):
    response: str

class UserAuth(BaseModel):
    email: str
    password: str
