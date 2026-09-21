import asyncio

import pytest
from fastapi.testclient import TestClient

from loja_assistente.request_limits import MAX_REQUEST_BYTES, RequestBodyLimit


@pytest.mark.parametrize("declared", [None, b"1", b"16385", b"invalid"])
def test_streamed_request_is_rejected_before_application(declared: bytes | None) -> None:
    async def scenario() -> None:
        called = False
        chunks = iter(
            [
                {"type": "http.request", "body": b"x" * MAX_REQUEST_BYTES, "more_body": True},
                {"type": "http.request", "body": b"y", "more_body": False},
            ]
        )
        messages = []

        async def application(*_args):
            nonlocal called
            called = True

        async def receive():
            return next(chunks)

        async def send(message):
            messages.append(message)

        await RequestBodyLimit(application)(
            {
                "type": "http",
                "method": "POST",
                "headers": [] if declared is None else [(b"content-length", declared)],
                "state": {"request_id": "test-id"},
            },
            receive,
            send,
        )
        assert not called
        assert messages[0]["status"] == 413
        assert b"test-id" in messages[1]["body"]

    asyncio.run(scenario())


def test_inclusive_limit_preserves_all_bytes_and_disconnect_does_not_call_app() -> None:
    async def scenario() -> None:
        received = []
        chunks = iter(
            [
                {"type": "http.request", "body": b"x" * 8192, "more_body": True},
                {"type": "http.request", "body": b"y" * 8192, "more_body": False},
            ]
        )

        async def application(_scope, receive, _send):
            received.append(await receive())

        async def receive():
            return next(chunks)

        async def disconnected():
            return {"type": "http.disconnect"}

        async def send(_message):
            pass

        scope = {"type": "http", "method": "POST", "headers": []}
        middleware = RequestBodyLimit(application)
        await middleware(scope, receive, send)
        assert received == [
            {"type": "http.request", "body": b"x" * 8192 + b"y" * 8192, "more_body": False}
        ]
        await middleware(scope, disconnected, send)
        assert len(received) == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/assistant/query"])
def test_public_413_keeps_context_without_echoing_body(path: str, client: TestClient) -> None:
    response = client.post(
        path, content=b"SECRET" * 3000, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "SECRET" not in response.text
