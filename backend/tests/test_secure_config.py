import pytest
from pydantic import ValidationError

from loja_assistente.config import Settings


@pytest.mark.parametrize(
    "invalid", [{"cookie_secure": False}, {"openai_base_url": "http://invalid.example"}]
)
def test_configuration_errors_and_representation_hide_synthetic_secrets(invalid):
    markers = [
        "SYNTHETIC_SESSION_MARKER_" * 3,
        "SYNTHETIC_PROVIDER_MARKER",
        "SYNTHETIC_DATABASE_MARKER",
    ]
    values = dict(
        _env_file=None,
        demo_mode=False,
        cookie_secure=True,
        session_secret=markers[0],
        openai_api_key=markers[1],
        database_url="postgresql://user:" + markers[2] + "@localhost/test",
    )
    valid = Settings(**values)
    assert all(marker not in repr(valid) for marker in markers)
    with pytest.raises(ValueError) as error:
        Settings(**(values | invalid))
    assert "input_value" not in str(error.value)
    assert all(marker not in str(error.value) for marker in markers)


def test_production_refuses_insecure_cookie() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(_env_file=None, demo_mode=False, session_secret="x" * 48, cookie_secure=False)
    assert Settings(
        _env_file=None, demo_mode=False, session_secret="x" * 48, cookie_secure=True
    ).cookie_secure


def test_local_demo_can_use_http_cookie() -> None:
    assert not Settings(_env_file=None, demo_mode=True, cookie_secure=False).cookie_secure
