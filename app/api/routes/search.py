# app/api/routes/search.py
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SearchServiceDep, SettingsDep
from app.api.schemas.errors import INVALID_INPUT
from app.api.schemas.search import SearchHitOut, SearchOut

router = APIRouter(prefix="/search", tags=["search"], responses=INVALID_INPUT)

Question = Annotated[str, Query(min_length=2, max_length=300, description="A question, in Arabic or English")]
NOTHING_FOUND = "Nothing in the clinic's documents answers this question."


@router.get("")
async def search(
    q: Question,
    service: SearchServiceDep,
    settings: SettingsDep,
    top_k: Annotated[int | None, Query(ge=1, le=20)] = None,
) -> SearchOut:
    """Find the document chunks that answer a question. Arabic and English questions both work.

    An empty list with found=false is a real answer: none of the documents is relevant enough.
    """
    result = await service.search(q, top_k or settings.SEARCH_TOP_K)
    hits = [
        SearchHitOut(
            chunk_id=h.chunk.id,
            document_id=h.chunk.document_id.hex,
            document_name=h.chunk.document.name,
            page=h.chunk.page,
            section=h.chunk.section,
            text=h.chunk.text,
            score=round(h.score, 3),
        )
        for h in result.hits
    ]
    return SearchOut(query=q, found=bool(hits), message=None if hits else NOTHING_FOUND, results=hits)
