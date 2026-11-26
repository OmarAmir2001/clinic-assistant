# labs/json_in_words.py
"""Ask the model for JSON in words only (no form). Can our code read each reply, and is it the right shape?

    uv run python -m labs.json_in_words

The API must be running (for /search). The model is called directly, like Session 1's ask.py.
"""
import json

import httpx
from openai import OpenAI

from app.core.config import get_settings
from labs.helpers import API

QUESTIONS = [
    "Do you take Allianz cards?",
    "How much is a dermatology visit?",
    "When does Dr. Omar Nabil work?",
    "Do you do LASIK eye surgery?",
    "بكام كشف الجلدية؟",
    "لازم أصوم قبل تحليل السكر؟",
    "بتقبلوا تأمين ميتلايف؟",
    "العيادة عنوانها إيه؟",
]
RULES = (
    "You are the assistant of Nile Family Clinic. Answer only from the numbered evidence. "
    "Reply with JSON only, exactly like this: "
    '{"answer": "...", "sources": [1], "answered": true}'
)

if __name__ == "__main__":
    settings = get_settings()
    client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY.get_secret_value(),
                    timeout=settings.LLM_TIMEOUT_SECONDS)
    broken = wrong = 0
    for question in QUESTIONS:
        hits = httpx.get(f"{API}/search", params={"q": question, "top_k": 3}, timeout=120).json()["results"]
        evidence = "\n\n".join(f"[{n}] {hit['text']}" for n, hit in enumerate(hits, start=1)) or "(none)"
        messages = [
            {"role": "system", "content": RULES},
            {"role": "user", "content": f"Evidence:\n{evidence}\n\nQuestion: {question}"},
        ]
        reply = client.chat.completions.create(model=settings.LLM_MODEL, messages=messages).choices[0].message.content
        try:
            data = json.loads(reply)
        except json.JSONDecodeError as error:
            broken += 1
            print(f"BROKEN     {question}\n           {error}\n           the reply: {reply[:90]!r}")
            continue
        # It is JSON, but is it the shape we asked for?
        if not (isinstance(data, dict) and isinstance(data.get("answer"), str)
                and isinstance(data.get("sources"), list) and isinstance(data.get("answered"), bool)):
            wrong += 1
            print(f"WRONG SHAPE {question}\n           the reply: {reply[:90]!r}")
            continue
        print(f"OK         {question}")
    print(f"\n{broken} of {len(QUESTIONS)} replies were not JSON; {wrong} were JSON of the wrong shape")
