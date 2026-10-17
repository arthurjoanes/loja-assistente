from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from loja_assistente.auth.service import Principal, require_csrf
from loja_assistente.config import settings
from loja_assistente.models import LoginSession


@pytest.mark.parametrize(
    "token,stored_token,accepted",
    [
        (b"\xff", "expected-token", False),
        (b"incorrect", "expected-token", False),
        (b"", "expected-token", False),
        (b"expected-token", "expected-token", True),
        (None, "", False),
        (b"", "", False),
    ],
)
def test_csrf_header_validation(token: bytes | None, stored_token: str, accepted: bool) -> None:
    headers = [
        (b"origin", settings.allowed_origins[0].encode()),
        (b"cookie", b"la_session=synthetic-session"),
    ]
    if token is not None:
        headers.append((b"x-csrf-token", token))
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "headers": headers,
        }
    )
    db = Mock(spec=Session)
    db.get.return_value = LoginSession(
        id="synthetic-digest",
        tenant_id="tenant",
        user_id="user",
        csrf_token=stored_token,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    principal = Principal("user", "tenant", "User", "user@example.com", "manager")

    if accepted:
        assert require_csrf(request, principal, db) == principal
    else:
        with pytest.raises(HTTPException) as failure:
            require_csrf(request, principal, db)
        assert failure.value.status_code == 403
