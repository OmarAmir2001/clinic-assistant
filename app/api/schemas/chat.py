# app/api/schemas/chat.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
        examples=["Is Dr. Mona Adel available on Thursday, and how much is the visit?"],
    )


class ChatResponse(BaseModel):
    answer: str
