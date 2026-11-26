# ui/client.py
"""How the chat page talks to our API: plain HTTP, like any other client. The UI never imports the app."""
import json
from collections.abc import Iterator
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Event:
    """One Server-Sent Event from /chat/stream: its name (status, token, ...) and its data."""
    kind: str
    data: dict


class APIError(Exception):
    """The API could not do it. The message is safe to show to the patient."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def read_events(lines: Iterator[str]) -> Iterator[Event]:
    """Turn the stream's lines into events. 'event: x' names it, 'data: {...}' carries it, an empty line ends it."""
    kind, data = "message", []
    for line in lines:
        if line == "":  # the end of one event
            if data:
                yield Event(kind, json.loads("\n".join(data)))
            kind, data = "message", []
        elif line.startswith(":"):
            continue  # a comment, like the ": ping" FastAPI sends when nothing happened for 15 seconds
        elif line.startswith("event:"):
            kind = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data.append(line.removeprefix("data:").removeprefix(" "))


def error_message(response: httpx.Response) -> str:
    """Our API's error shape: {"error": {"message": ...}}. Anything else: a plain sentence."""
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return f"The server answered {response.status_code}."


class ClinicAPI:
    def __init__(self, base_url: str, timeout_seconds: float):
        # read: the most we wait between two pieces of the stream (the server pings every 15 seconds)
        self.http = httpx.Client(base_url=base_url, timeout=httpx.Timeout(timeout_seconds, connect=5))

    def health(self) -> bool:
        try:
            return self.http.get("/health").status_code == 200
        except httpx.HTTPError:
            return False

    def chat(self, conversation_id: str | None, message: str) -> Iterator[Event]:
        """Send one message; get the agent's events as they happen. The last one is "done" or "error"."""
        try:
            with self.http.stream("POST", "/chat/stream",
                                  json={"conversation_id": conversation_id, "message": message}) as response:
                if response.status_code != 200:  # refused before the agent started, like a message that's too long
                    response.read()
                    raise APIError(error_message(response))
                yield from read_events(response.iter_lines())
        except httpx.ConnectError as error:
            raise APIError("The clinic's server is not running. Start it, then try again.") from error
        except httpx.TimeoutException as error:
            raise APIError("The server took too long to answer. Please try again.") from error

    def upload(self, name: str, content: bytes) -> dict:
        """Upload a clinic document (Session 4's POST /documents)."""
        try:
            response = self.http.post("/documents", files={"file": (name, content)})
        except httpx.HTTPError as error:
            raise APIError("The clinic's server is not running. Start it, then try again.") from error
        if response.status_code not in (200, 201):
            raise APIError(error_message(response))
        return response.json()
