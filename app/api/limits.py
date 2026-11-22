# app/api/limits.py
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import error_response


class BodySizeLimit:
    """Stops any request bigger than `max_bytes` while it is still arriving, before it fills the disk."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # 1. The size the client says it will send. Only a claim, but rejecting early is cheap
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            response = error_response(413, "file_too_large", self._message())
            return await response(scope, receive, send)

        # 2. The bytes that really arrive, counted piece by piece
        received = 0

        async def counting_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise HTTPException(status_code=413, detail=self._message())
            return message

        await self.app(scope, counting_receive, send)

    def _message(self) -> str:
        return f"The request is bigger than the {self.max_bytes // (1024 * 1024)} MB limit."
