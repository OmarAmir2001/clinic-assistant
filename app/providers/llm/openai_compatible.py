# app/providers/llm/openai_compatible.py
import logging
from dataclasses import dataclass

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import UnavailableError

logger = logging.getLogger(__name__)


class LLMError(UnavailableError):
    """The language model could not give us an answer."""


@dataclass
class LLMReply:
    """What the model wrote, and what it cost."""
    text: str
    tokens_in: int
    tokens_out: int


class OpenAICompatibleLLM:
    """Talks to any OpenAI-compatible LLM server (Gemini, Ollama, ...). Which one is decided by .env."""

    def __init__(self, settings: Settings):
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY.get_secret_value(),
            timeout=settings.LLM_TIMEOUT_SECONDS,  # the most one try may take
            max_retries=settings.LLM_MAX_RETRIES,  # our choice, not the client's hidden default of 2
        )

    def chat(self, messages: list[dict]) -> LLMReply:
        """Send a conversation to the model and return its reply."""
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature
            )
        except OpenAIError as error:
            logger.error("LLM call failed: %s", error)
            raise LLMError("The assistant is not available right now. Please try again later.") from error
        return self._reply(response, response.choices[0].message.content)

    def fill_form(self, messages: list[dict], form: type[BaseModel]) -> tuple[BaseModel, LLMReply]:
        """Ask the model to fill in a form (a Pydantic model) instead of writing free text."""
        try:
            response = self.client.chat.completions.parse(
                model=self.model, messages=messages, response_format=form, temperature=self.temperature
            )
        except (OpenAIError, ValidationError) as error:
            # ValidationError: the server sent something that doesn't fit the form
            logger.error("LLM call failed: %s", error)
            raise LLMError("The assistant is not available right now. Please try again later.") from error
        message = response.choices[0].message
        if message.parsed is None:
            logger.error("The model did not fill the form: %r", message.refusal or message.content)
            raise LLMError("The assistant could not answer this question. Please try again later.")
        return message.parsed, self._reply(response, message.content)

    def _reply(self, response, text: str) -> LLMReply:
        reply = LLMReply(text=text, tokens_in=response.usage.prompt_tokens, tokens_out=response.usage.completion_tokens)
        logger.info("LLM call done: %d tokens in, %d tokens out", reply.tokens_in, reply.tokens_out)
        return reply
