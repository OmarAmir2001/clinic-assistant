# app/services/agent.py
"""The clinic agent: the model picks tools, our code runs them, in a loop with strict limits."""
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date

from fastapi.concurrency import iterate_in_threadpool

from app.core.config import Settings
from app.core.enums import EventKind, Role, ToolName
from app.core.errors import NotFoundError
from app.db.models import Conversation, Message
from app.prompts.loader import Prompt
from app.providers.llm.openai_compatible import LLMReply, OpenAICompatibleLLM, ToolCall
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

# What the patient sees while the agent works (Session 10): one line for each thing it can be doing
READING = {"en": "Reading your message…", "ar": "أقرأ رسالتك…"}
THINKING = {"en": "Reading what I found…", "ar": "أراجع ما وجدته…"}
DOING = {
    "en": {ToolName.SEARCH_CLINIC_DOCS: "Checking the clinic's documents…",
           ToolName.LIST_DOCTORS: "Looking at the list of doctors…",
           ToolName.CHECK_AVAILABILITY: "Looking up free times…",
           ToolName.BOOK_APPOINTMENT: "Preparing the booking…",
           ToolName.GET_APPOINTMENT: "Finding your appointment…",
           ToolName.CANCEL_OR_RESCHEDULE: "Preparing the change…"},
    "ar": {ToolName.SEARCH_CLINIC_DOCS: "أبحث في مستندات العيادة…",
           ToolName.LIST_DOCTORS: "أراجع قائمة الأطباء…",
           ToolName.CHECK_AVAILABILITY: "أبحث عن المواعيد المتاحة…",
           ToolName.BOOK_APPOINTMENT: "أجهّز الحجز…",
           ToolName.GET_APPOINTMENT: "أبحث عن موعدك…",
           ToolName.CANCEL_OR_RESCHEDULE: "أجهّز التغيير…"},
}
SAVING = {"en": "Saving the change…", "ar": "أحفظ التغيير…"}


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
class Event:
    """One thing to tell the patient while the agent works (Session 10): what kind, and its data."""
    kind: EventKind
    data: dict


def done(reply: str, waiting: bool = False) -> Event:
    """The loop's answer: the reply, and whether it waits for a yes."""
    return Event(EventKind.DONE, {"reply": reply, "waiting_for_confirmation": waiting})


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
        """The whole reply at once (Session 9's /chat): run the stream and keep only its last event."""
        async for event in self.stream(conversation_id, text):
            if event.kind == EventKind.DONE:
                done = event.data
        return AgentReply(uuid.UUID(done["conversation_id"]), done["reply"], done["waiting_for_confirmation"],
                          done["tools_used"])

    async def stream(self, conversation_id: uuid.UUID | None, text: str) -> AsyncIterator[Event]:
        """One patient message in; events out while the agent works (Session 10). The last one is DONE."""
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
            yield Event(EventKind.STATUS, {"text": SAVING[language]})
            call = ToolCall(id=pending["id"], name=pending["tool"], arguments=pending["arguments"])
            turn.add(assistant_message("", [call]))
            result = await self.tools.run(call)
            turn.add(tool_message(call, result))
            turn.tools_used.append(call.name)
            if "error" not in json.loads(result):  # done: show what changed (an error goes to the model instead)
                yield Event(EventKind.CHANGED, {"result": json.loads(result), "details": pending["details"]})

        # 3. The loop: the model, then tools, then the model again... until it answers, or a limit stops it
        reply, waiting = GAVE_UP[language], False
        async for event in self.loop(turn, conversation, language):
            if event.kind == EventKind.DONE:  # the loop's answer: ours to finish below
                reply, waiting = event.data["reply"], event.data["waiting_for_confirmation"]
            else:
                yield event
        turn.add({"role": Role.ASSISTANT, "content": reply})

        # 4. Save this turn's messages, all together. Then the last event: the whole reply
        for message in turn.new:
            self.memory.add(conversation.id, message)
        await self.memory.save()
        yield Event(EventKind.DONE, {"conversation_id": str(conversation.id), "reply": reply,
                                     "waiting_for_confirmation": waiting, "tools_used": turn.tools_used})

    async def loop(self, turn: Turn, conversation: Conversation, language: str) -> AsyncIterator[Event]:
        tokens = 0
        for step in range(1, self.settings.AGENT_MAX_STEPS + 1):
            first = step == 1 and not turn.tools_used  # after a "yes", the model reads the change we just made
            yield Event(EventKind.STATUS, {"text": READING[language] if first else THINKING[language]})
            reply = None
            async for piece in iterate_in_threadpool(self.llm.stream(turn.messages, SPECS)):
                if isinstance(piece, LLMReply):
                    reply = piece  # the last item: the whole reply
                else:
                    yield Event(EventKind.TOKEN, {"text": piece})  # the patient reads while the model writes
            tokens += reply.tokens_in + reply.tokens_out
            if not reply.tool_calls:
                yield done(reply.text.strip() or GAVE_UP[language])  # no tool asked for: the answer (never empty)
                return

            turn.add(assistant_message(reply.text, reply.tool_calls))
            for call in reply.tool_calls:
                logger.info("Step %d: the model asks for %s", step, call.name)
                turn.tools_used.append(call.name)
                yield Event(EventKind.STATUS, {"text": DOING[language].get(call.name, THINKING[language])})
                tool = TOOLS.get(call.name)
                if tool is not None and tool.writes:
                    result = await self.propose(call, conversation, language)
                else:
                    result = await self.tools.run(call)
                    found = json.loads(result)
                    if "evidence" in found:  # search_clinic_docs found something: show the patient what it read
                        yield Event(EventKind.SOURCES, {"sources": found["evidence"]})
                turn.add(tool_message(call, result))

            if conversation.pending_action:
                pending = conversation.pending_action
                yield Event(EventKind.CONFIRM, {"text": pending["confirm"], "details": pending["details"]})
                yield done(pending["confirm"], waiting=True)  # our words, not the model's
                return
            if tokens > self.settings.AGENT_TOKEN_BUDGET:
                logger.warning("Stopped: this message used %d tokens (budget %d)", tokens,
                               self.settings.AGENT_TOKEN_BUDGET)
                yield done(GAVE_UP[language])
                return

        logger.warning("Stopped after %d steps without an answer", self.settings.AGENT_MAX_STEPS)
        yield done(GAVE_UP[language])

    async def propose(self, call: ToolCall, conversation: Conversation, language: str) -> str:
        """A change (book, cancel, move) never runs when the model asks. We show it to the patient and wait."""
        if conversation.pending_action:
            return as_json({"error": "One change at a time. Wait for the patient's answer first."})
        preview = await self.tools.preview(call, language)
        if "error" in preview:
            return as_json(preview)  # the model reads the problem and fixes the call
        # Keep exactly what we showed. Its new id doubles as the booking's idempotency key: one "yes" books once
        conversation.pending_action = {"id": str(uuid.uuid4()), "tool": call.name, "arguments": preview["arguments"],
                                       "confirm": preview["confirm"], "details": preview["details"]}
        return as_json(WAITING)
