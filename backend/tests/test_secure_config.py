import pytest
from pydantic import ValidationError

from loja_assistente.config import Settings


def test_production_refuses_insecure_cookie() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(_env_file=None, demo_mode=False, session_secret="x" * 48, cookie_secure=False)
    assert Settings(
        _env_file=None, demo_mode=False, session_secret="x" * 48, cookie_secure=True
    ).cookie_secure


def test_local_demo_can_use_http_cookie() -> None:
    assert not Settings(_env_file=None, demo_mode=True, cookie_secure=False).cookie_secure
