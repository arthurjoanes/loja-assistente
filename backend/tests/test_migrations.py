import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import Principal
from loja_assistente.favorites.contracts import SaveFavoriteRequest
from loja_assistente.favorites.service import save_favorite
from loja_assistente.models import FavoriteRecord


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    """Create and remove only a UUID database owned by this individual test.

    This bypasses the data fixture's TRUNCATE entirely. Compose's isolated test
    role can create a database; a restricted role must be granted CREATEDB for
    this integration check. No existing database is reset or reused.
    """
    configured = os.environ.get("MIGRATION_TEST_DATABASE_URL") or os.environ.get(
        "TEST_DATABASE_URL"
    )
    if not configured:
        pytest.skip("TEST_DATABASE_URL não configurada: migrações PostgreSQL não executadas.")
    source = make_url(configured)
    if source.get_backend_name() != "postgresql" or not (source.database or "").endswith("_test"):
        raise RuntimeError("A conexão de migração deve apontar para PostgreSQL exclusivo *_test.")
    if os.environ.get("MIGRATION_TEST_DATABASE_URL") and source == make_url(
        os.environ.get("TEST_DATABASE_URL", "sqlite://")
    ):
        raise RuntimeError("MIGRATION_TEST_DATABASE_URL deve ser diferente de TEST_DATABASE_URL.")
    name = "la_migration_" + uuid4().hex + "_test"
    if not re.fullmatch(r"la_migration_[a-f0-9]{32}_test", name):
        raise RuntimeError("Nome de banco temporário inválido.")
    target = source.set(database=name)
    if target == source or not name.endswith("_test"):
        raise RuntimeError("O teste de migração exige seu próprio banco temporário.")
    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = create_engine(target, pool_pre_ping=True)
    created = False
    try:
        with admin.connect() as connection:
            if connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ):
                raise RuntimeError(
                    "O nome de banco temporário já existe; ele não será reutilizado."
                )
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        yield engine
    finally:
        engine.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def configuration(engine: Engine) -> Config:
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False).replace("%", "%%")
    )
    return config


def upgrade(engine: Engine, revision: str) -> None:
    config = configuration(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


def test_empty_install_matches_models_at_0006(migration_engine: Engine) -> None:
    upgrade(migration_engine, "head")
    with migration_engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006"
        tables = inspect(connection).get_table_names()
        assert {"favorites", "provider_reservations", "login_sessions"}.issubset(tables)
        constraints = inspect(connection).get_foreign_keys("favorites")
        source = next(item for item in constraints if item["name"] == "fk_favorites_source_owner")
        assert source["constrained_columns"] == ["tenant_id", "user_id", "source_answer_id"]
        assert source["referred_columns"] == ["tenant_id", "user_id", "id"]
        config = configuration(migration_engine)
        config.attributes["connection"] = connection
        command.check(config)


def test_upgrade_0004_preserves_legacy_json_sessions_and_unknown_ledger(
    migration_engine: Engine,
) -> None:
    upgrade(migration_engine, "0004")
    now = datetime.now(UTC)
    plan = {
        "intent": "aggregate",
        "metric": "revenue",
        "store_references": ["legacy-store"],
        "period": {"start": "2026-08-16", "end": "2026-08-17"},
        "comparison": None,
        "grouping": None,
        "limit": 5,
    }
    legacy = {
        "id": "legacy-answer",
        "conversation_id": "legacy-conversation",
        "question": "Quanto vendi ontem?",
        "status": "ready",
        "message": "Cálculo registrado",
        "mode": "demo",
        "plan": plan,
        "result": {
            "intent": "aggregate",
            "metric": "revenue",
            "scope": [{"id": "legacy-store", "name": "Centro"}],
            "period": plan["period"],
            "timezone": "America/Sao_Paulo",
            "currency": "BRL",
            "unit": "centavos",
            "formula": "Receita líquida",
            "value": "9007199254740993",
            "totals": {
                "revenue_cents": 9_007_199_254_740_993,
                "orders": 1,
                "units": 1,
                "average_ticket_cents": "9007199254740993",
            },
            "rows": [],
            "coverage": {
                "status": "complete",
                "covered_days": 1,
                "expected_days": 1,
                "missing": [],
            },
            "comparison": None,
            "evidence": [],
            "dataset_version": "legacy-dataset",
            "request_id": "legacy-request",
        },
        "request_id": "legacy-request",
        "created_at": now.isoformat(),
    }
    metadata = MetaData()
    metadata.reflect(bind=migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(
            metadata.tables["organizations"].insert(), {"id": "legacy-tenant", "name": "Legacy"}
        )
        connection.execute(
            metadata.tables["users"].insert(),
            {
                "id": "legacy-user",
                "tenant_id": "legacy-tenant",
                "name": "Legacy",
                "email": "legacy@example.invalid",
                "role": "manager",
                "password_hash": "preserved",
            },
        )
        connection.execute(
            metadata.tables["stores"].insert(),
            {
                "tenant_id": "legacy-tenant",
                "id": "legacy-store",
                "external_id": "STORE",
                "name": "Centro",
            },
        )
        connection.execute(
            metadata.tables["store_permissions"].insert(),
            {
                "tenant_id": "legacy-tenant",
                "user_id": "legacy-user",
                "store_id": "legacy-store",
            },
        )
        connection.execute(
            metadata.tables["conversations"].insert(),
            {
                "id": "legacy-conversation",
                "tenant_id": "legacy-tenant",
                "user_id": "legacy-user",
                "title": "Legado",
                "created_at": now,
                "last_plan": plan,
            },
        )
        connection.execute(
            metadata.tables["answers"].insert(),
            {
                "id": "legacy-answer",
                "tenant_id": "legacy-tenant",
                "user_id": "legacy-user",
                "conversation_id": "legacy-conversation",
                "payload": legacy,
                "created_at": now,
            },
        )
        connection.execute(
            metadata.tables["login_sessions"].insert(),
            {
                "id": "legacy-session-digest",
                "tenant_id": "legacy-tenant",
                "user_id": "legacy-user",
                "csrf_token": "fixture-csrf",
                "expires_at": now + timedelta(hours=1),
                "created_at": now,
            },
        )
        connection.execute(
            metadata.tables["provider_budget_accounts"].insert(),
            {
                "tenant_id": "legacy-tenant",
                "calls_limit": 2,
                "input_limit": 1000,
                "output_limit": 1000,
                "committed_calls": 1,
                "committed_input": 100,
                "committed_output": 100,
                "blocked": False,
                "blocked_reason": None,
                "configured_reason": "Fixture",
                "updated_at": now,
            },
        )
        connection.execute(
            metadata.tables["provider_reservations"].insert(),
            {
                "tenant_id": "legacy-tenant",
                "call_id": "legacy-call",
                "request_id": "legacy-request",
                "user_id": "legacy-user",
                "model_requested": "fixture-no-provider",
                "reserved_input": 100,
                "reserved_output": 100,
                "state": "unknown",
                "created_at": now,
                "dispatched_at": now,
            },
        )
        connection.execute(
            metadata.tables["login_admission"].insert(),
            {
                "key": "legacy-admission",
                "window_start": now,
                "attempts": 2,
            },
        )
        before = {
            name: [dict(row._mapping) for row in connection.execute(select(metadata.tables[name]))]
            for name in (
                "answers",
                "login_sessions",
                "provider_budget_accounts",
                "provider_reservations",
                "login_admission",
            )
        }
    upgrade(migration_engine, "head")
    with migration_engine.connect() as connection:
        for name, rows in before.items():
            assert [
                dict(row._mapping) for row in connection.execute(select(metadata.tables[name]))
            ] == rows
        conversation = connection.execute(
            text(
                "SELECT last_plan, pending_clarification, clarification_revision FROM conversations WHERE id = 'legacy-conversation'"
            )
        ).one()
        assert conversation.last_plan == plan
        assert (
            conversation.pending_clarification is None and conversation.clarification_revision == 0
        )
        assert Answer.model_validate(legacy).result is not None
    with Session(migration_engine) as db:
        favorite = save_favorite(
            db,
            Principal(
                "legacy-user", "legacy-tenant", "Legacy", "legacy@example.invalid", "manager"
            ),
            SaveFavoriteRequest(answer_id="legacy-answer", name="Legado preservado"),
        )
        assert favorite.plan.model_dump(mode="json") == plan
        assert db.get(FavoriteRecord, favorite.id) is not None
