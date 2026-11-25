# app/api/schemas/search.py
from pydantic import BaseModel


class SearchHitOut(BaseModel):
    chunk_id: int
    document_id: str
    document_name: str  # the source, so the answer can say where it came from (Session 8)
    page: int | None
    section: str | None
    text: str
    score: float  # the reranker's score, 0 to 1


class SearchOut(BaseModel):
    query: str
    found: bool  # False: nothing in the clinic's documents is relevant enough
    message: str | None = None
    results: list[SearchHitOut]
