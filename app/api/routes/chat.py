import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.api.dependencies import AgentServiceDep
from app.api.schemas.chat import ChatOut, ChatRequest
from app.api.schemas.errors import INVALID_INPUT, ErrorResponse
from app.core.enums import EventKind
from app.core.errors import AppError

logger = logging.getLogger(__name__)
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


@router.post("/stream", response_class=EventSourceResponse)
async def chat_stream(request: ChatRequest, agent: AgentServiceDep) -> AsyncIterator[ServerSentEvent]:
    """The same agent, as Server-Sent Events: each step, then the answer as it is written, then "done".

    The status code (200) is sent before the agent starts, so a problem can't become a 404 or a 503 any more.
    It comes as the last event instead: "error", with the same code and message as the error responses."""
    try:
        async for event in agent.stream(request.conversation_id, request.message):
            yield ServerSentEvent(event=event.kind, data=event.data)
    except AppError as error:
        yield ServerSentEvent(event=EventKind.ERROR, data={"code": error.code, "message": error.message})
    except Exception:
        logger.exception("The chat stream failed")  # the full error, for us, in the log
        yield ServerSentEvent(event=EventKind.ERROR,
                              data={"code": "internal_error", "message": "Something went wrong on our side."})
