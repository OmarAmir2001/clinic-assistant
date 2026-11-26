"""Read a conversation back from the database, turn by turn: what the patient said, which tools the model
asked for and with what, what each tool returned, and the reply. This is how we find WHERE an answer went wrong.

    uv run python -m labs.trace                  # the newest conversation
    uv run python -m labs.trace <conversation_id>
"""
import asyncio
import json
import sys
import textwrap

from sqlalchemy import select

from app.core.config import get_settings
from app.db.database import make_engine, make_sessions
from app.db.models import Conversation, Message
from app.services.tools import masked

WIDTH = 100


def short(text: str, size: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= size else text[:size] + " …"


def result_text(content: str) -> str:
    """A tool's result, shortened. For a search: which documents it found, and how each one starts."""
    try:
        result = json.loads(content)
    except ValueError:
        return short(content)
    if "evidence" in result:
        return "found: " + " | ".join(f"[{e['source']}] {short(e['text'], 60)}" for e in result["evidence"])
    return short(json.dumps(result, ensure_ascii=False))


def show(label: str, text: str) -> None:
    lines = textwrap.wrap(text, WIDTH - 12) or [""]
    print(f"  {label:<9} {lines[0]}")
    for line in lines[1:]:
        print(f"  {'':<9} {line}")


async def main(conversation_id: str | None) -> None:
    engine = make_engine(get_settings().DATABASE_URL)
    async with make_sessions(engine)() as session:
        if conversation_id is None:
            newest = select(Conversation).order_by(Conversation.started_at.desc()).limit(1)
            conversation = await session.scalar(newest)
        else:
            conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            raise SystemExit("No such conversation.")
        query = select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id)
        messages = list(await session.scalars(query))
    await engine.dispose()

    print(f"Conversation {conversation.id}")
    turn = 0
    for m in messages:
        if m.role == "user":
            turn += 1
            print(f"\nTurn {turn}")
            show("You", m.content)
        elif m.role == "assistant" and m.tool_calls:
            if m.content.strip():
                show("model", m.content)
            for call in m.tool_calls:
                function = call["function"]
                show("model →", f"{function['name']} {masked(function['arguments'])}")
        elif m.role == "tool":
            show("tool ←", result_text(m.content))
        else:
            show("Agent", m.content)
    if conversation.pending_action:
        print(f"\n  (waiting for a yes: {conversation.pending_action['tool']})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
