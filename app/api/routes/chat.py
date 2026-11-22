# app/api/routes/chat.py
from fastapi import APIRouter

from app.api.dependencies import AnswerServiceDep
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse

router = APIRouter(prefix="/chat", tags=["chat"], responses=INVALID_INPUT)


@router.post("", responses={503: {"model": ErrorResponse, "description": "The language model is not available"}})
def chat(request: ChatRequest, service: AnswerServiceDep) -> ChatResponse:
    """Answer a patient's question from the clinic's information."""
    return ChatResponse(answer=service.answer(request.message))
