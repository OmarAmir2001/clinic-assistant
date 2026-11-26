# app/repositories/conversations.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message


class ConversationRepository:
    """Every database question about conversations: the agent's memory."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(self) -> Conversation:
        conversation = Conversation(id=uuid.uuid4())
        self.session.add(conversation)
        await self.session.flush()  # write the row now: its messages will point at it
        return conversation

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def recent(self, conversation_id: uuid.UUID, limit: int) -> list[Message]:
        # The newest `limit` messages, then turned back to oldest-first, the order the model reads them
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(reversed(list(await self.session.scalars(query))))

    def add(self, conversation_id: uuid.UUID, message: dict) -> None:
        self.session.add(Message(
            conversation_id=conversation_id,
            role=message["role"],
            content=message.get("content") or "",
            tool_calls=message.get("tool_calls"),
            tool_call_id=message.get("tool_call_id"),
        ))

    async def save(self) -> None:
        # Everything added in this turn is saved together: all of it, or none of it
        await self.session.commit()
