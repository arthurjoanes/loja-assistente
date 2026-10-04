from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from manual_fixture import PASSWORD
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from loja_assistente.auth import admission, routes
from loja_assistente.models import LoginAdmission


def test_failed_logins_persist_and_reject_before_argon2(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"email": "gerente.a@demo.local", "password": "incorrect"}
    for _ in range(admission.ACCOUNT_LIMIT):
        assert client.post("/api/auth/login", json=payload).status_code == 401
    verify = Mock(side_effect=AssertionError("An exhausted quota must not invoke Argon2"))
    monkeypatch.setattr(routes, "verify_password", verify)
    # Case, whitespace and X-Forwarded-For cannot reset the account's allowance.
    response = client.post(
        "/api/auth/login",
        json={"email": " GERENTE.A@DEMO.LOCAL ", "password": PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.42"},
    )
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= admission.WINDOW_SECONDS
    assert response.headers["cache-control"] == "no-store"
    verify.assert_not_called()


def test_source_quota_limits_varying_unknown_accounts(client: TestClient) -> None:
    for number in range(admission.SOURCE_LIMIT):
        response = client.post(
            "/api/auth/login",
            json={"email": f"unknown-{number}@example.invalid", "password": "bad"},
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "another@example.invalid", "password": "bad"}
        ).status_code
        == 429
    )


def test_success_releases_only_its_reservation(client: TestClient, db: Session) -> None:
    assert (
        client.post(
            "/api/auth/login", json={"email": "gerente.a@demo.local", "password": "bad"}
        ).status_code
        == 401
    )
    for _ in range(6):
        assert (
            client.post(
                "/api/auth/login", json={"email": "gerente.a@demo.local", "password": PASSWORD}
            ).status_code
            == 200
        )
    row = db.get(LoginAdmission, admission.key_for("account\0gerente.a@demo.local"))
    assert row is not None and row.attempts == 1


def test_durable_expiry_and_concurrent_distributed_account_admission(
    test_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "SessionLocal", sessionmaker(bind=test_engine))
    marker = uuid4().hex
    email = marker + "@example.invalid"
    sources = [marker + str(number) for number in range(10)]
    keys = [admission.key_for("account\0" + email)] + [
        admission.key_for("source\0" + source) for source in sources
    ]

    def request(source: str) -> int:
        try:
            admission.admit_login(email, source)
            return 200
        except HTTPException as error:
            return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(request, sources))
        assert results.count(200) == admission.ACCOUNT_LIMIT
        assert results.count(429) == 10 - admission.ACCOUNT_LIMIT
        # A new process would use the same persisted rows, without an in-memory counter.
        with Session(test_engine) as session:
            row = session.get(LoginAdmission, keys[0])
            assert row is not None and row.attempts == admission.ACCOUNT_LIMIT
            row.window_start = datetime.now(UTC) - timedelta(seconds=admission.WINDOW_SECONDS + 1)
            session.commit()
        assert request(sources[0]) == 200
        with Session(test_engine) as session:
            assert all(
                len(row.key) == 64 and marker not in row.key
                for row in session.scalars(select(LoginAdmission))
            )
    finally:
        with test_engine.begin() as connection:
            connection.execute(delete(LoginAdmission).where(LoginAdmission.key.in_(keys)))


def test_expiry_is_independent_of_the_cleanup_batch(
    test_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "SessionLocal", sessionmaker(bind=test_engine))
    marker = uuid4().hex
    email = marker + "@example.invalid"
    source = marker + "source"
    keys = [admission.key_for(marker + str(number)) for number in range(150)]
    keys += [admission.key_for("account\0" + email), admission.key_for("source\0" + source)]
    expired = datetime.now(UTC) - timedelta(seconds=admission.WINDOW_SECONDS + 1)
    try:
        with Session(test_engine) as session:
            session.add_all(
                LoginAdmission(key=key, window_start=expired, attempts=admission.SOURCE_LIMIT)
                for key in keys
            )
            session.commit()
        assert len(admission.admit_login(email, source)) == 2
        with Session(test_engine) as session:
            for key in keys[-2:]:
                row = session.get(LoginAdmission, key)
                assert row is not None and row.attempts == 1 and row.window_start > expired
    finally:
        with test_engine.begin() as connection:
            connection.execute(delete(LoginAdmission).where(LoginAdmission.key.in_(keys)))
