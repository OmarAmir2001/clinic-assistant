"""Chat with the running API's agent from the terminal. Every message goes to the same conversation.

    uv run python -m labs.chat                                   # type your messages, an empty line ends
    uv run python -m labs.chat "Is Dr. Mona free on Thursday?" "Book the second one"   # or give them here
"""
import sys
import time

import httpx

from labs.helpers import API


def send(client: httpx.Client, conversation_id: str | None, message: str) -> str | None:
    start = time.perf_counter()
    response = client.post("/chat", json={"conversation_id": conversation_id, "message": message})
    seconds = time.perf_counter() - start
    body = response.json()
    if response.status_code != 200:
        print(f"   {response.status_code} after {seconds:.1f}s: {body['error']['message']}")
        return conversation_id
    tools = ", ".join(body["tools_used"]) or "no tools"
    print(f"Agent: {body['reply']}")
    print(f"   ({seconds:.1f}s, {tools}{', waiting for yes' if body['waiting_for_confirmation'] else ''})")
    return body["conversation_id"]


if __name__ == "__main__":
    conversation_id = None
    with httpx.Client(base_url=API, timeout=600) as client:
        messages = sys.argv[1:]
        while True:
            message = messages.pop(0) if messages else (None if sys.argv[1:] else input("You: "))
            if not message:
                break
            if sys.argv[1:]:
                print(f"You: {message}")
            conversation_id = send(client, conversation_id, message)
            print()
