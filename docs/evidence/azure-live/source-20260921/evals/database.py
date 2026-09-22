"""Banco isolado para testes e avaliações, preparado pelas migrações reais."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url


def prepare_test_database(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise RuntimeError("O banco deve ser PostgreSQL dedicado e seu nome terminar em _test.")
    backend = Path(__file__).resolve().parents[1] / "backend"
    configuration = Config(str(backend / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend / "migrations"))
    configuration.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            configuration.attributes["connection"] = connection
            command.upgrade(configuration, "head")
    except Exception:
        engine.dispose()
        raise
    return engine
