"""Send the model one question with our six tools, and print what comes back. Nothing is run.

    uv run python -m labs.first_call "Which dermatologist is free on Sunday?"
"""
import sys
from datetime import date

from app.core.config import get_settings
from app.prompts.loader import load_prompt
from app.providers.llm.openai_compatible import OpenAICompatibleLLM
from app.services.tools import SPECS, calendar

if __name__ == "__main__":
    settings = get_settings()
    prompt = load_prompt("agent", settings.AGENT_PROMPT_VERSION)
    messages = [prompt.system(calendar=calendar(date.today())), prompt.user(message=" ".join(sys.argv[1:]))]

    reply = OpenAICompatibleLLM(settings).chat(messages, tools=SPECS)
    print(f"text:       {reply.text!r}")
    print(f"tool calls: {len(reply.tool_calls)}")
    for call in reply.tool_calls:
        print(f"  id={call.id}  name={call.name}  arguments={call.arguments}")
    print(f"tokens:     {reply.tokens_in} in, {reply.tokens_out} out")
