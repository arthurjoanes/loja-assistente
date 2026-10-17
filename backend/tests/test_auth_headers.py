from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from loja_assistente.auth.service import Principal, require_csrf
from loja_assistente.config import settings
from loja_assistente.models import LoginSession


@pytest.mark.parametrize(
    "token,accepted",
    [(b"\xff", False), (b"incorrect", False), (b"", False), (b"expected-token", True)],
)
def test_csrf_header_validation(token: bytes, accepted: bool) -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [
                (b"origin", settings.allowed_origins[0].encode()),
                (b"cookie", b"la_session=synthetic-session"),
                (b"x-csrf-token", token),
            ],
        }
    )
    db = Mock(spec=Session)
    db.get.return_value = LoginSession(
        id="synthetic-digest",
        tenant_id="tenant",
        user_id="user",
        csrf_token="expected-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    principal = Principal("user", "tenant", "User", "user@example.com", "manager")

    if accepted:
        assert require_csrf(request, principal, db) == principal
    else:
        with pytest.raises(HTTPException) as failure:
            require_csrf(request, principal, db)
        assert failure.value.status_code == 403
