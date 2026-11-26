from fastapi import APIRouter

from app.api.dependencies import AgentServiceDep
from app.api.schemas.chat import ChatOut, ChatRequest
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse

router = APIRouter(prefix="/chat", tags=["chat"], responses=INVALID_INPUT)


@router.post(
    "",
    responses={
        404: {"model": ErrorResponse, "description": "No conversation with this id"},
        503: {"model": ErrorResponse, "description": "The language model is not available"},
    },
)
async def chat(request: ChatRequest, agent: AgentServiceDep) -> ChatOut:
    """Talk to the clinic's agent. It answers from the documents and the schedule, and books only after a yes."""
    result = await agent.chat(request.conversation_id, request.message)
    return ChatOut(
        conversation_id=result.conversation_id,
        reply=result.text,
        waiting_for_confirmation=result.waiting_for_confirmation,
        tools_used=result.tools_used,
    )
