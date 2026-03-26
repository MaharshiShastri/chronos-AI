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

class PlanRequest(BaseModel):
    task: str
    time_budget: int #In seconds
    mode: str="fast" #Fast is default mode, otherwise deep

class PlanStep(BaseModel):
    step: str
    time_allocated: int

class PlanResponse(BaseModel):
    plan: list[PlanStep]
    total_time: int

