import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = Field(default=None, description="Leave it out to start a new conversation")
    message: str = Field(min_length=1, max_length=1000, examples=["Which dermatologist is free on Thursday?"])


class ChatOut(BaseModel):
    conversation_id: uuid.UUID  # send it with the next message, so the agent remembers this conversation
    reply: str
    waiting_for_confirmation: bool  # True: the reply asks the patient to confirm a change
    tools_used: list[str]  # which tools the agent called for this reply, in order
