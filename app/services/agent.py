# app/services/agent.py
"""The clinic agent: the model picks tools, our code runs them, in a loop with strict limits."""
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import date

from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.enums import Role
from app.core.errors import NotFoundError
from app.db.models import Conversation, Message
from app.prompts.loader import Prompt
from app.providers.llm.openai_compatible import OpenAICompatibleLLM, ToolCall
from app.repositories.conversations import ConversationRepository
from app.services.answer import ARABIC
from app.services.tools import SPECS, TOOLS, ClinicTools, as_json, calendar

logger = logging.getLogger(__name__)

YES = {"yes", "y", "ok", "okay", "sure", "confirm", "نعم", "أيوه", "ايوه", "تمام", "موافق", "أكيد", "اكيد"}
GAVE_UP = {
    "en": "Sorry, I couldn't finish this. Please try again, or call the clinic's reception.",
    "ar": "عذرًا، لم أستطع إكمال طلبك. حاول مرة أخرى، أو اتصل باستقبال العيادة.",
}
WAITING = {"status": "waiting_for_patient", "message": "Nothing is changed yet. The patient is asked to confirm."}


def is_yes(text: str) -> bool:
    """Does the patient's message start with a yes? ("yes", "Yes, book it", "نعم")"""
    words = re.findall(r"\w+", text.lower())
    return bool(words) and words[0] in YES


def assistant_message(text: str, calls: list[ToolCall]) -> dict:
    """The model's reply in the shape the model expects to see again: its text and the tools it asked for."""
    message = {"role": Role.ASSISTANT, "content": text}
    if calls:
        message["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}} for c in calls
        ]
    return message


def tool_message(call: ToolCall, result: str) -> dict:
    """A tool's result. tool_call_id says which of the model's calls it answers."""
    return {"role": Role.TOOL, "tool_call_id": call.id, "content": result}


def as_message(row: Message) -> dict:
    """A stored message, back in the shape the model reads."""
    message = {"role": row.role, "content": row.content}
    if row.tool_calls:
        message["tool_calls"] = row.tool_calls
    if row.tool_call_id:
        message["tool_call_id"] = row.tool_call_id
    return message


@dataclass
class Turn:
    """Everything that happens between one patient message and our reply."""
    messages: list[dict]  # what the model sees: the rules, the history, and this turn so far
    new: list[dict] = field(default_factory=list)  # only this turn's messages: saved at the end
    tools_used: list[str] = field(default_factory=list)

    def add(self, message: dict) -> None:
        self.messages.append(message)
        self.new.append(message)


@dataclass(frozen=True)
class AgentReply:
    conversation_id: uuid.UUID
    text: str
    waiting_for_confirmation: bool  # True: the reply asks the patient to confirm a change
    tools_used: list[str]


class AgentService:
    """One patient message in, one reply out. The model decides which tools; our code runs them, within limits."""

    def __init__(self, llm: OpenAICompatibleLLM, prompt: Prompt, tools: ClinicTools,
                 memory: ConversationRepository, settings: Settings):
        self.llm = llm
        self.prompt = prompt
        self.tools = tools
        self.memory = memory
        self.settings = settings

    async def chat(self, conversation_id: uuid.UUID | None, text: str) -> AgentReply:
        # 1. The conversation so far, from the database (or a new one)
        if conversation_id is None:
            conversation = await self.memory.start()
        else:
            conversation = await self.memory.get(conversation_id)
            if conversation is None:
                raise NotFoundError(f"There is no conversation {conversation_id}. Start a new one.")
        stored = await self.memory.recent(conversation.id, self.settings.AGENT_HISTORY_MESSAGES)
        history = [as_message(m) for m in stored]
        while history and history[0]["role"] != Role.USER:
            history.pop(0)  # start at a patient's message: never with a tool result whose call was cut off

        language = "ar" if ARABIC.search(text) else "en"
        turn = Turn(messages=[self.prompt.system(calendar=calendar(date.today())), *history])
        turn.add(self.prompt.user(message=text))

        # 2. Did we ask for a confirmation last time? A "yes" runs that exact change now. Anything else drops it
        pending, conversation.pending_action = conversation.pending_action, None
        if pending and is_yes(text):
            call = ToolCall(id=pending["id"], name=pending["tool"], arguments=pending["arguments"])
            turn.add(assistant_message("", [call]))
            turn.add(tool_message(call, await self.tools.run(call)))
            turn.tools_used.append(call.name)

        # 3. The loop: the model, then tools, then the model again... until it answers, or a limit stops it
        reply, waiting = await self.loop(turn, conversation, language)
        turn.add({"role": Role.ASSISTANT, "content": reply})

        # 4. Save this turn's messages, all together
        for message in turn.new:
            self.memory.add(conversation.id, message)
        await self.memory.save()
        return AgentReply(conversation.id, reply, waiting, turn.tools_used)

    async def loop(self, turn: Turn, conversation: Conversation, language: str) -> tuple[str, bool]:
        tokens = 0
        for step in range(1, self.settings.AGENT_MAX_STEPS + 1):
            reply = await run_in_threadpool(self.llm.chat, turn.messages, SPECS)
            tokens += reply.tokens_in + reply.tokens_out
            if not reply.tool_calls:
                return reply.text.strip() or GAVE_UP[language], False  # no tool asked for: the answer (never empty)

            turn.add(assistant_message(reply.text, reply.tool_calls))
            for call in reply.tool_calls:
                logger.info("Step %d: the model asks for %s", step, call.name)
                turn.tools_used.append(call.name)
                tool = TOOLS.get(call.name)
                if tool is not None and tool.writes:
                    result = await self.propose(call, conversation, language)
                else:
                    result = await self.tools.run(call)
                turn.add(tool_message(call, result))

            if conversation.pending_action:
                return conversation.pending_action["confirm"], True  # our words, not the model's
            if tokens > self.settings.AGENT_TOKEN_BUDGET:
                logger.warning("Stopped: this message used %d tokens (budget %d)", tokens,
                               self.settings.AGENT_TOKEN_BUDGET)
                return GAVE_UP[language], False

        logger.warning("Stopped after %d steps without an answer", self.settings.AGENT_MAX_STEPS)
        return GAVE_UP[language], False

    async def propose(self, call: ToolCall, conversation: Conversation, language: str) -> str:
        """A change (book, cancel, move) never runs when the model asks. We show it to the patient and wait."""
        if conversation.pending_action:
            return as_json({"error": "One change at a time. Wait for the patient's answer first."})
        preview = await self.tools.preview(call, language)
        if "error" in preview:
            return as_json(preview)  # the model reads the problem and fixes the call
        # Keep exactly what we showed. Its new id doubles as the booking's idempotency key: one "yes" books once
        conversation.pending_action = {"id": str(uuid.uuid4()), "tool": call.name,
                                       "arguments": preview["arguments"], "confirm": preview["confirm"]}
        return as_json(WAITING)
