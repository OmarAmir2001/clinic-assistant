# app/api/schemas/answer.py
from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500, examples=["Do you take Allianz cards?"])


class SourceOut(BaseModel):
    document_name: str
    section: str | None
    page: int | None


class AnswerOut(BaseModel):
    question: str
    answered: bool  # False: an honest "I don't know", never a guess
    answer: str
    sources: list[SourceOut]  # where the answer came from; empty when answered is False
