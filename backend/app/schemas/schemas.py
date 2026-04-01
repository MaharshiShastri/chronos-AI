from pydantic import BaseModel, EmailStr, Field, AliasChoices
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str

class UserAuth(BaseModel):
    email: str
    password: str

class PlanRequest(BaseModel):
    task: str
    time_budget: int #In seconds
    mode: str="fast" #Fast is default mode, otherwise deep
    conversation_id: Optional[int] = None

class PlanStep(BaseModel):
    step: str = Field(validation_alias=AliasChoices('step', 'name', 'description'))
    time_allocated: int

class PlanResponse(BaseModel):
    plan: list[PlanStep]
    total_time: int

class StatusUpdate(BaseModel):
    status: str
