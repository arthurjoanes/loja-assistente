from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest
from conftest import authenticate
from fastapi import HTTPException
from fastapi.testclient import TestClient
from manual_fixture import ORIGIN
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from loja_assistente.assistant import service as assistant_service
from loja_assistente.assistant.interpreters import openai_adapter
from loja_assistente.auth.service import Principal, session_digest
from loja_assistente.clarifications import service
from loja_assistente.clarifications.contracts import ClarificationResponse
from loja_assistente.config import settings
from loja_assistente.conversations.service import get_conversation
from loja_assistente.models import (
    AnswerRecord,
    Conversation,
    Coverage,
    LoginSession,
    Store,
    StorePermission,
)


def ask(client: TestClient, question: str = "Receita da loja Centro", **extra) -> dict:
    response = client.post(
        "/api/assistant/query", json={"question": question, "mode": "demo", **extra}
    )
    assert response.status_code == 200, response.text
    return response.json()


def choice_body(answer: dict, choice_id: str = "yesterday") -> dict:
    pending = answer["pending_clarification"]
    return {"pending_id": pending["id"], "revision": pending["revision"], "choice_id": choice_id}


def respond(client: TestClient, answer: dict, choice_id: str = "yesterday"):
    return client.post(
        f"/api/conversations/{answer['conversation_id']}/clarification/respond",
        json=choice_body(answer, choice_id),
    )


def test_missing_period_survives_reload_and_completes_deterministically(
    manager_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = ask(manager_client)
    pending = first["pending_clarification"]
    assert first["plan"] is None and first["result"] is None
    assert pending["partial_plan"]["metric"] == "revenue"
    assert pending["partial_plan"]["store_ids"] == ["a001"]
    saved = db.get(Conversation, first["conversation_id"])
    assert saved is not None and saved.last_plan is None
    detail = manager_client.get("/api/conversations/" + first["conversation_id"])
    assert detail.json()["pending_clarification"] == pending
    listed = manager_client.get("/api/conversations").json()
    assert listed[0]["pending_clarification"] == pending
    interpreter = Mock(side_effect=AssertionError("Resolver escolha não deve reinterpretar"))
    monkeypatch.setattr(assistant_service, "interpret_request", interpreter)
    monkeypatch.setattr(openai_adapter, "interpret", interpreter)
    monkeypatch.setattr(settings, "reference_date", date(2026, 10, 12))
    response = respond(manager_client, first)
    assert response.status_code == 200, response.text
    final = response.json()
    assert final["result"]["value"] == "3000"
    assert final["plan"]["metric"] == "revenue"
    assert final["plan"]["store_references"] == ["a001"]
    assert final["plan"]["period"] == {"start": "2026-08-16", "end": "2026-08-17"}
    assert final["pending_clarification"]["status"] == "resolved"
    assert final["clarification_response"]["choice_id"] == "yesterday"
    assert final["request_id"] != first["request_id"]
    assert manager_client.get("/api/answers/" + final["id"]).json() == final
    assert db.get(AnswerRecord, first["id"]).payload == first
    assert saved.last_plan == final["plan"]
    interpreter.assert_not_called()
    assert respond(manager_client, first).status_code == 409


def test_duplicate_names_preserve_metric_period_and_ids(
    supervisor_client: TestClient, db: Session
) -> None:
    store = db.get(Store, ("org_a", "a002"))
    assert store is not None
    store.name = "Centro"
    db.commit()
    first = ask(
        supervisor_client,
        "Receita da loja Centro ontem",
        period={"start": "2026-08-10", "end": "2026-08-17"},
    )
    pending = first["pending_clarification"]
    assert pending["missing_field"] == "store"
    assert pending["partial_plan"]["period"] == {"start": "2026-08-16", "end": "2026-08-17"}
    assert [choice["store_ids"] for choice in pending["choices"]] == [["a001"], ["a002"]]
    assert all(choice["store_ids"][0] in choice["label"] for choice in pending["choices"])
    response = respond(supervisor_client, first, "store:a002")
    assert response.status_code == 200, response.text
    assert response.json()["result"]["value"] == "1600"
    assert response.json()["plan"]["store_references"] == ["a002"]


def test_two_missing_fields_form_two_sequential_pendings(
    supervisor_client: TestClient, db: Session
) -> None:
    store = db.get(Store, ("org_a", "a002"))
    assert store is not None
    store.name = "Centro"
    db.commit()
    first = ask(supervisor_client, "Unidades da loja Centro")
    response = respond(supervisor_client, first, "store:a002")
    assert response.status_code == 200, response.text
    second = response.json()
    assert second["result"] is None
    assert second["pending_clarification"]["missing_field"] == "period"
    assert second["pending_clarification"]["id"] != first["pending_clarification"]["id"]
    assert second["pending_clarification"]["revision"] > first["pending_clarification"]["revision"]
    assert second["pending_clarification"]["partial_plan"]["store_ids"] == ["a002"]
    assert second["pending_clarification"]["partial_plan"]["metric"] == "units"
    assert respond(supervisor_client, first, "store:a001").status_code == 409
    final = respond(supervisor_client, second)
    assert final.status_code == 200 and final.json()["result"]["value"] == "2"
    messages = supervisor_client.get("/api/conversations/" + first["conversation_id"]).json()[
        "messages"
    ]
    assert len(messages) == 3
    assert messages[1]["clarification_response"]["choice_id"] == "store:a002"


def test_new_question_invalidates_previous_choice_without_wrong_execution(
    manager_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = ask(manager_client)
    second = ask(
        manager_client, "Unidades da loja Centro", conversation_id=first["conversation_id"]
    )
    query = Mock(side_effect=AssertionError("Escolha velha não deve executar"))
    monkeypatch.setattr(service, "execute_query", query)
    assert respond(manager_client, first).status_code == 409
    query.assert_not_called()
    assert second["pending_clarification"]["partial_plan"]["metric"] == "units"


def test_cancel_persists_and_rejects_repeat_or_late_choice(manager_client: TestClient) -> None:
    first = ask(manager_client)
    body = choice_body(first)
    del body["choice_id"]
    path = f"/api/conversations/{first['conversation_id']}/clarification/cancel"
    cancelled = manager_client.post(path, json=body)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    detail = manager_client.get("/api/conversations/" + first["conversation_id"]).json()
    assert detail["pending_clarification"] == cancelled.json()
    assert manager_client.post(path, json=body).status_code == 409
    assert respond(manager_client, first).status_code == 409


def test_invalid_choice_and_injected_plan_leave_current_pending_intact(
    manager_client: TestClient, db: Session
) -> None:
    first = ask(manager_client)
    unknown = respond(manager_client, first, "choice-from-another-pending")
    assert unknown.status_code == 409
    path = f"/api/conversations/{first['conversation_id']}/clarification/respond"
    injected = manager_client.post(path, json={**choice_body(first), "plan": {"metric": "units"}})
    assert injected.status_code == 422
    saved = db.get(Conversation, first["conversation_id"])
    assert saved.pending_clarification == first["pending_clarification"]
    assert saved.last_plan is None
    final = respond(manager_client, first)
    assert final.status_code == 200 and final.json()["plan"]["metric"] == "revenue"


def test_expiration_uses_real_clock_and_never_accepts_old_choice(
    manager_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from loja_assistente.clarifications import state

    first = ask(manager_client)
    future = datetime.fromisoformat(first["pending_clarification"]["expires_at"]) + timedelta(
        seconds=1
    )
    monkeypatch.setattr(state, "utcnow", lambda: future)
    detail = manager_client.get("/api/conversations/" + first["conversation_id"])
    assert detail.status_code == 200
    assert detail.json()["pending_clarification"]["status"] == "expired"
    response = respond(manager_client, first)
    assert response.status_code == 409 and "expirado" in response.text
    saved = db.get(Conversation, first["conversation_id"])
    assert saved.pending_clarification["status"] == "expired" and saved.last_plan is None


@pytest.mark.parametrize("identity", ["supervisor_a", "manager_b"])
def test_pending_is_personal_to_user_and_tenant(manager_client: TestClient, identity: str) -> None:
    from loja_assistente.app import app

    first = ask(manager_client)
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as other:
        authenticate(other, identity)
        assert other.get("/api/conversations/" + first["conversation_id"]).status_code == 404
        assert respond(other, first).status_code == 404
        body = choice_body(first)
        del body["choice_id"]
        assert (
            other.post(
                f"/api/conversations/{first['conversation_id']}/clarification/cancel", json=body
            ).status_code
            == 404
        )
        assert first["conversation_id"] not in other.get("/api/conversations").text


@pytest.mark.parametrize("kind", ["csrf", "origin", "expired_session", "logout"])
def test_pending_mutations_require_session_origin_and_csrf(
    manager_client: TestClient, db: Session, kind: str
) -> None:
    first = ask(manager_client)
    expected = 403
    if kind == "csrf":
        manager_client.headers["X-CSRF-Token"] = "invalid"
    elif kind == "origin":
        manager_client.headers["Origin"] = "https://attacker.invalid"
    elif kind == "expired_session":
        token = manager_client.cookies.get("la_session")
        session = db.get(LoginSession, session_digest(token))
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        expected = 401
    else:
        assert manager_client.post("/api/auth/logout", json={}).status_code == 200
        expected = 401
    assert respond(manager_client, first).status_code == expected
    body = choice_body(first)
    del body["choice_id"]
    assert (
        manager_client.post(
            f"/api/conversations/{first['conversation_id']}/clarification/cancel", json=body
        ).status_code
        == expected
    )
    saved = db.get(Conversation, first["conversation_id"])
    assert saved.pending_clarification["status"] == "pending"
    assert saved.last_plan is None


def test_revocation_between_question_and_choice_hides_scope_before_query(
    supervisor_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = ask(supervisor_client, "Receita da loja Jardins")
    db.execute(
        delete(StorePermission).where(
            StorePermission.user_id == "supervisor_a", StorePermission.store_id == "a002"
        )
    )
    db.commit()
    query = Mock(side_effect=AssertionError("Loja revogada não deve executar"))
    monkeypatch.setattr(service, "execute_query", query)
    listed = supervisor_client.get("/api/conversations")
    assert first["conversation_id"] not in listed.text and "Jardins" not in listed.text
    for path in ["/api/conversations/" + first["conversation_id"], "/api/answers/" + first["id"]]:
        denied = supervisor_client.get(path)
        assert denied.status_code == 403 and "Jardins" not in denied.text
    assert respond(supervisor_client, first).status_code == 403
    query.assert_not_called()


def test_revoked_historical_partial_hides_title_after_valid_new_question(
    supervisor_client: TestClient, db: Session
) -> None:
    first = ask(supervisor_client, "Receita da loja Jardins")
    ask(supervisor_client, "Receita da loja Centro ontem", conversation_id=first["conversation_id"])
    db.execute(
        delete(StorePermission).where(
            StorePermission.user_id == "supervisor_a", StorePermission.store_id == "a002"
        )
    )
    db.commit()
    listed = supervisor_client.get("/api/conversations")
    assert "Jardins" not in listed.text and first["conversation_id"] not in listed.text
    assert (
        supervisor_client.get("/api/conversations/" + first["conversation_id"]).status_code == 403
    )


@pytest.mark.parametrize(
    "question",
    [
        "Receita da loja Centro e da loja Norte",
        "Receita da loja Centro e da loja Fantasma",
        "Receita da loja Centro e da loja b001",
    ],
)
def test_missing_period_or_ambiguous_scope_does_not_offer_forbidden_choices(
    supervisor_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, question: str
) -> None:
    store = db.get(Store, ("org_a", "a002"))
    store.name = "Centro"
    db.commit()
    query = Mock(side_effect=AssertionError("Escopo misto não deve ler vendas"))
    monkeypatch.setattr(assistant_service, "execute_query", query)
    response = supervisor_client.post(
        "/api/assistant/query", json={"question": question, "mode": "demo"}
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Escopo de loja não autorizado."}
    query.assert_not_called()


@pytest.mark.parametrize(
    "question", ["Receita em dinheiro", "Receita por vendedor", "Receita do produto Caneca"]
)
def test_unsupported_filter_has_no_pending_executable_plan(
    manager_client: TestClient, question: str
) -> None:
    answer = ask(manager_client, question)
    assert answer["pending_clarification"] is None
    assert answer["plan"] is None and answer["result"] is None
    assert (
        manager_client.get("/api/conversations/" + answer["conversation_id"]).json()[
            "pending_clarification"
        ]
        is None
    )


def test_no_store_selection_keeps_permitted_total_and_explicit_period_wins(
    supervisor_client: TestClient,
) -> None:
    answer = ask(
        supervisor_client,
        "Quanto vendi ontem?",
        period={"start": "2026-08-10", "end": "2026-08-17"},
    )
    assert answer["pending_clarification"] is None
    assert answer["plan"]["store_references"] == ["a001", "a002"]
    assert answer["result"]["value"] == "4600"
    assert answer["plan"]["period"] == {"start": "2026-08-16", "end": "2026-08-17"}


def test_provider_error_does_not_resolve_pending_or_accept_old_revision(
    manager_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = ask(manager_client)
    provider = Mock(side_effect=openai_adapter.ProviderUnavailable("Timeout simulado"))
    monkeypatch.setattr(assistant_service, "interpret_request", provider)
    failed = manager_client.post(
        "/api/assistant/query",
        json={
            "question": "Receita da loja Centro",
            "mode": "llm",
            "conversation_id": first["conversation_id"],
        },
    )
    assert failed.status_code == 200
    answer = failed.json()
    pending = answer["pending_clarification"]
    assert answer["status"] == "provider_error" and pending["status"] == "pending"
    assert pending["id"] == first["pending_clarification"]["id"]
    assert pending["revision"] > first["pending_clarification"]["revision"]
    assert respond(manager_client, first).status_code == 409
    resolved = respond(manager_client, answer)
    assert resolved.status_code == 200 and resolved.json()["result"]["value"] == "3000"
    provider.assert_called_once()


@pytest.mark.parametrize("tampering", ["schema", "choice", "partial"])
def test_tampered_persisted_pending_never_executes(
    manager_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, tampering: str
) -> None:
    first = ask(manager_client)
    conversation = db.get(Conversation, first["conversation_id"])
    payload = {**conversation.pending_clarification}
    if tampering == "schema":
        payload["schema_version"] = 2
    elif tampering == "choice":
        payload["choices"] = [
            {"id": "yesterday", "label": "Inválido", "store_ids": ["a001"], "period": None}
        ]
    else:
        payload["partial_plan"] = {**payload["partial_plan"], "limit": 99}
    conversation.pending_clarification = payload
    db.commit()
    query = Mock(side_effect=AssertionError("Pendência inválida não pode executar"))
    monkeypatch.setattr(service, "execute_query", query)
    assert respond(manager_client, first).status_code == 409
    query.assert_not_called()


def test_absent_coverage_completes_without_turning_absence_into_zero(
    manager_client: TestClient, db: Session
) -> None:
    first = ask(manager_client)
    db.execute(
        delete(Coverage).where(
            Coverage.tenant_id == "org_a",
            Coverage.store_id == "a001",
            Coverage.date == date(2026, 8, 16),
        )
    )
    db.commit()
    response = respond(manager_client, first)
    assert response.status_code == 200
    final = response.json()
    assert final["status"] == "no_data"
    assert final["result"]["value"] is None and final["result"]["totals"] is None
    assert final["result"]["coverage"]["status"] == "absent"
    assert final["pending_clarification"]["status"] == "resolved"


def test_partial_coverage_and_comparison_limits_survive_resolution(
    manager_client: TestClient, db: Session
) -> None:
    first = ask(manager_client, "Compare receita da loja Centro com o período anterior")
    db.execute(
        delete(Coverage).where(
            Coverage.tenant_id == "org_a",
            Coverage.store_id == "a001",
            Coverage.date == date(2026, 8, 16),
        )
    )
    db.commit()
    final = respond(manager_client, first, "last_7_days")
    assert final.status_code == 200, final.text
    result = final.json()["result"]
    assert result["coverage"]["status"] == "partial"
    assert result["value"] == "4100"
    assert result["comparison"]["change_percent"] is None
    assert "faltam dados" in result["comparison"]["message"]


def test_conversation_nowait_and_stale_choice_use_independent_connections(
    manager_client: TestClient, db: Session, test_engine: Engine
) -> None:
    first = ask(manager_client)
    principal = Principal("manager_a", "org_a", "manager_a", "gerente.a@demo.local", "manager")
    mutation = ClarificationResponse.model_validate(choice_body(first))
    with Session(test_engine) as lock_owner, Session(test_engine) as contender:
        get_conversation(lock_owner, principal, first["conversation_id"], lock=True)
        with pytest.raises(HTTPException) as blocked:
            service.respond_to_clarification(
                contender, principal, first["conversation_id"], mutation, "competing-choice"
            )
        assert blocked.value.status_code == 409
        lock_owner.commit()
        answer = service.respond_to_clarification(
            contender, principal, first["conversation_id"], mutation, "winning-choice"
        )
        assert answer.result.value == "3000"
    with Session(test_engine) as old_tab:
        with pytest.raises(HTTPException) as stale:
            service.respond_to_clarification(
                old_tab, principal, first["conversation_id"], mutation, "old-tab-choice"
            )
        assert stale.value.status_code == 409
    db.expire_all()
    assert (
        len(
            list(
                db.scalars(
                    select(AnswerRecord).where(
                        AnswerRecord.conversation_id == first["conversation_id"]
                    )
                )
            )
        )
        == 2
    )
