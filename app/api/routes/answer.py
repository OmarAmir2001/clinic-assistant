# app/api/routes/answer.py
from fastapi import APIRouter

from app.api.dependencies import AnswerServiceDep
from app.api.schemas.answer import AnswerOut, AnswerRequest, SourceOut
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse

router = APIRouter(prefix="/answer", tags=["answer"], responses=INVALID_INPUT)


@router.post("", responses={503: {"model": ErrorResponse, "description": "The language model is not available"}})
async def answer(request: AnswerRequest, service: AnswerServiceDep) -> AnswerOut:
    """Answer a patient's question from the clinic's documents, with its sources, or say "I don't know"."""
    result = await service.answer(request.question)
    return AnswerOut(
        question=request.question,
        answered=result.answered,
        answer=result.text,
        sources=[SourceOut(document_name=c.document.name, section=c.section, page=c.page) for c in result.sources],
    )
