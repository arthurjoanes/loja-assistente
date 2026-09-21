from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from manual_fixture import ORIGIN, PASSWORD
from sqlalchemy.orm import Session

from loja_assistente.auth.service import session_digest
from loja_assistente.config import settings
from loja_assistente.models import LoginSession


def test_login_hash_cookie_profile_and_logout(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "gerente.a@demo.local", "password": PASSWORD}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "la_session=" in cookie
    token = client.cookies["la_session"]
    stored = db.get(LoginSession, session_digest(token))
    assert stored is not None and stored.id != token
    profile = response.json()
    assert profile["user"]["organization"]["id"] == "org_a"
    assert [store["id"] for store in profile["user"]["stores"]] == ["a001"]
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": profile["csrf_token"]})
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert db.get(LoginSession, session_digest(token)) is None


@pytest.mark.parametrize(
    "email,password", [("missing@demo.local", PASSWORD), ("gerente.a@demo.local", "bad-password")]
)
def test_failed_credentials_have_same_generic_error(
    client: TestClient, email: str, password: str
) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json() == {"detail": "E-mail ou senha inválidos."}


def test_expiration_uses_real_clock(manager_client: TestClient, db: Session) -> None:
    session = db.get(LoginSession, session_digest(manager_client.cookies["la_session"]))
    assert session is not None
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    response = manager_client.get("/api/auth/me")
    assert response.status_code == 401 and "expirada" in response.json()["detail"]


def test_csrf_and_origin_are_independent_controls(manager_client: TestClient) -> None:
    assert (
        manager_client.post("/api/auth/logout", headers={"X-CSRF-Token": "invalid"}).status_code
        == 403
    )
    assert (
        manager_client.post(
            "/api/auth/logout", headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert manager_client.get("/api/auth/me").status_code == 200
    assert manager_client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 200


def test_login_checks_origin_and_rejects_forged_identity_fields(client: TestClient) -> None:
    payload = {"email": "gerente.a@demo.local", "password": PASSWORD}
    assert (
        client.post(
            "/api/auth/login", json=payload, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert client.post("/api/auth/login", json={**payload, "tenant_id": "org_b"}).status_code == 422
    assert (
        client.get(
            "/api/auth/me", headers={"X-Tenant-ID": "org_a", "X-User-ID": "manager_a"}
        ).status_code
        == 401
    )


def test_fictitious_credentials_are_disabled_outside_demo(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    response = client.post(
        "/api/auth/login", json={"email": "gerente.a@demo.local", "password": PASSWORD}
    )
    assert response.status_code == 401
