import os
from collections.abc import Iterator
from datetime import date

import pytest
from evals.database import prepare_test_database
from fastapi.testclient import TestClient
from manual_fixture import IDENTITIES, ORIGIN, PASSWORD, seed_manual
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from loja_assistente.auth import admission
from loja_assistente.config import settings
from loja_assistente.database import Base, get_db


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada: testes PostgreSQL não executados.")
    engine = prepare_test_database(url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    monkeypatch.setattr(admission, "SessionLocal", sessionmaker(bind=test_engine))
    names = ", ".join('"' + table.name + '"' for table in Base.metadata.sorted_tables)
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    monkeypatch.setattr(settings, "dataset_version", "manual-v1")
    monkeypatch.setattr(settings, "reference_date", date(2026, 8, 17))
    # Real commits release advisory locks; a surrounding savepoint would keep
    # login reservations locked while the next independent admission waits.
    with Session(test_engine) as session:
        seed_manual(session)
        session.commit()
        yield session


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    from loja_assistente.app import app

    def override_database() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_database
    try:
        with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as http:
            yield http
    finally:
        app.dependency_overrides.clear()


def authenticate(client: TestClient, identity: str) -> TestClient:
    response = client.post(
        "/api/auth/login",
        json={
            "email": IDENTITIES[identity],
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


@pytest.fixture
def manager_client(client: TestClient) -> TestClient:
    return authenticate(client, "manager_a")


@pytest.fixture
def supervisor_client(client: TestClient) -> TestClient:
    return authenticate(client, "supervisor_a")


@pytest.fixture
def other_client(client: TestClient) -> TestClient:
    return authenticate(client, "manager_b")
