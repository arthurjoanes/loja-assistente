import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check.py"
TEST_URL = "postgresql+psycopg://test:test@localhost:5432/loja_assistente_test"
DEMO_URL = "postgresql+psycopg://demo:demo@localhost:5432/loja_assistente"


def load_check_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("loja_check_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url", ["", "not-a-url", "sqlite:///loja_assistente_test", DEMO_URL])
def test_invalid_database_guard_runs_no_command(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_check_script()
    execute = Mock()
    monkeypatch.setattr(module.subprocess, "run", execute)
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    with pytest.raises(SystemExit, match="PostgreSQL exclusivo"):
        module.main()
    execute.assert_not_called()


def test_every_check_receives_only_the_validated_test_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_check_script()
    execute = Mock()
    monkeypatch.setattr(module.subprocess, "run", execute)
    monkeypatch.setenv("TEST_DATABASE_URL", TEST_URL)
    monkeypatch.setenv("DATABASE_URL", DEMO_URL)
    module.main()
    assert execute.call_count == 6
    assert any(call.args[0] == ["alembic", "upgrade", "head"] for call in execute.call_args_list)
    for call in execute.call_args_list:
        assert call.kwargs["check"] is True
        assert call.kwargs["env"]["DATABASE_URL"] == TEST_URL
        assert call.kwargs["env"]["TEST_DATABASE_URL"] == TEST_URL
    assert module.os.environ["DATABASE_URL"] == DEMO_URL


def test_postgres_url_with_connection_options_is_valid() -> None:
    module = load_check_script()
    url = TEST_URL + "?sslmode=disable"
    result = module.test_environment({"TEST_DATABASE_URL": url, "DATABASE_URL": DEMO_URL})
    assert result["DATABASE_URL"] == url
