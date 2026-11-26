"""Watch the agent's events arrive, with the second each one came. Compare with labs/chat.py.

    uv run python -m labs.stream "Which dermatologist is free on Sunday?"
    uv run python -m labs.stream "Which dermatologist is free on Sunday?" "Book 18:00 for Omar Amir, 01012345678" "yes"
"""
import sys
import time

from labs.helpers import API
from ui.client import APIError, ClinicAPI


def show(api: ClinicAPI, conversation_id: str | None, message: str) -> str | None:
    print(f"You: {message}")
    start, writing = time.perf_counter(), False
    try:
        for event in api.chat(conversation_id, message):
            at = f"{time.perf_counter() - start:5.1f}s"
            if event.kind == "token":
                if not writing:
                    print(f"{at}  token   ", end="")
                    writing = True
                print(event.data["text"], end="", flush=True)  # the answer, as it is written
                continue
            if writing:
                print()
                writing = False
            if event.kind == "status":
                print(f"{at}  status  {event.data['text']}")
            elif event.kind == "sources":
                print(f"{at}  sources {', '.join(s['source'] for s in event.data['sources'])}")
            elif event.kind == "confirm":
                print(f"{at}  confirm " + " · ".join(f"{label}: {value}" for label, value in event.data["details"]))
            elif event.kind == "changed":
                print(f"{at}  changed {event.data['result']}")
            elif event.kind == "done":
                print(f"{at}  done    tools: {', '.join(event.data['tools_used']) or 'none'}")
                return event.data["conversation_id"]
            elif event.kind == "error":
                print(f"{at}  error   {event.data['message']}")
    except APIError as error:
        print(f"Could not send: {error.message}")
    return conversation_id


if __name__ == "__main__":
    api = ClinicAPI(API, timeout_seconds=600)
    conversation_id = None
    for message in sys.argv[1:]:
        conversation_id = show(api, conversation_id, message)
        print()
