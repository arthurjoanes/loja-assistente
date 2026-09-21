"""Bound JSON requests before the framework decodes their contents."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BYTES = 16 * 1024


class RequestBodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        async def too_large() -> None:
            response = JSONResponse(
                status_code=413,
                content={
                    "detail": "Requisição maior que 16 KiB.",
                    "request_id": scope.get("state", {}).get("request_id"),
                },
            )
            await response(scope, receive, send)

        for name, value in scope["headers"]:
            if name.lower() == b"content-length" and value.isdigit():
                normalized = value.lstrip(b"0")
                if len(normalized) > 5 or (normalized and int(normalized) > MAX_REQUEST_BYTES):
                    await too_large()
                    return

        # Count actual chunks too: Content-Length may be absent or inaccurate.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                await too_large()
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
