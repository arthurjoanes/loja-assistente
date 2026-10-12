from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Event
from typing import Any
from unittest.mock import Mock

import pytest
from conftest import authenticate
from fastapi import HTTPException
from fastapi.testclient import TestClient
from manual_fixture import ORIGIN
from pydantic import ValidationError
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from loja_assistente.auth.service import Principal
from loja_assistente.favorites import service
from loja_assistente.favorites.contracts import (
    FavoriteRevisionRequest,
    RenameFavoriteRequest,
    SaveFavoriteRequest,
)
from loja_assistente.models import (
    AnswerRecord,
    Coverage,
    Dataset,
    FavoriteRecord,
    LoginSession,
    OrderItem,
    StorePermission,
)


def ask(client: TestClient, question: str = "Quanto vendi ontem?") -> dict[str, Any]:
    response = client.post("/api/assistant/query", json={"question": question, "mode": "demo"})
    assert response.status_code == 200, response.text
    return response.json()


def save(client: TestClient, answer_id: str, name: str = "Receita Centro") -> dict[str, Any]:
    response = client.post("/api/favorites", json={"answer_id": answer_id, "name": name})
    assert response.status_code == 200, response.text
    return response.json()


def principal() -> Principal:
    return Principal("manager_a", "org_a", "manager_a", "gerente.a@demo.local", "manager")


@pytest.mark.parametrize("name", ["", "   ", "a" * 121, "primeira\nsegunda", "\x00"])
def test_favorite_names_are_limited_and_nonblank(name: str) -> None:
    with pytest.raises(ValidationError):
        SaveFavoriteRequest(answer_id="answer", name=name)


@pytest.mark.parametrize("revision", [0, -1, 1.5, "1", True])
def test_revision_requires_a_positive_integer(revision: object) -> None:
    with pytest.raises(ValidationError):
        FavoriteRevisionRequest.model_validate({"revision": revision})


def test_save_contract_cannot_accept_browser_authority_or_plan() -> None:
    for field in ("tenant_id", "user_id", "plan", "schema_version"):
        with pytest.raises(ValidationError):
            SaveFavoriteRequest.model_validate({"answer_id": "answer", "name": "Nome", field: {}})
    assert SaveFavoriteRequest(answer_id="answer", name="  Receita  ").name == "Receita"


def test_save_list_rename_delete_with_idempotence_and_revisions(manager_client: TestClient) -> None:
    answer = ask(manager_client)
    favorite = save(manager_client, answer["id"])
    assert favorite["plan"] == answer["plan"]
    assert favorite["schema_version"] == 1 and favorite["revision"] == 1
    assert favorite["source_answer_id"] == answer["id"]
    duplicate = save(manager_client, answer["id"], "Não sobrescrever nome")
    assert duplicate == favorite
    assert manager_client.get("/api/favorites").json() == [favorite]
    assert manager_client.get("/api/favorites/" + favorite["id"]).json() == favorite
    rename = manager_client.post(
        f"/api/favorites/{favorite['id']}/rename", json={"name": "Novo nome", "revision": 1}
    )
    assert rename.status_code == 200
    renamed = rename.json()
    assert renamed["name"] == "Novo nome" and renamed["revision"] == 2
    stale = manager_client.post(
        f"/api/favorites/{favorite['id']}/rename", json={"name": "Nome antigo", "revision": 1}
    )
    assert stale.status_code == 409
    assert (
        manager_client.post(
            f"/api/favorites/{favorite['id']}/delete", json={"revision": 1}
        ).status_code
        == 409
    )
    deletion = manager_client.post(f"/api/favorites/{favorite['id']}/delete", json={"revision": 2})
    assert deletion.status_code == 204 and not deletion.content
    assert manager_client.get("/api/favorites").json() == []
    assert manager_client.get("/api/favorites/" + favorite["id"]).status_code == 404
    assert manager_client.get("/api/answers/" + answer["id"]).json() == answer


@pytest.mark.parametrize("identity", ["manager_b", "supervisor_a"])
def test_favorites_and_source_answers_are_personal(
    manager_client: TestClient, identity: str
) -> None:
    from loja_assistente.app import app

    answer = ask(manager_client)
    favorite = save(manager_client, answer["id"], "Título privado Centro")
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as other:
        authenticate(other, identity)
        assert other.get("/api/favorites").json() == []
        denied_save = other.post(
            "/api/favorites", json={"answer_id": answer["id"], "name": "Tentativa"}
        )
        assert denied_save.status_code == 404
        for action, body in (
            ("rename", {"name": "Tentativa", "revision": 1}),
            ("delete", {"revision": 1}),
            ("run", {"revision": 1}),
        ):
            response = other.post(f"/api/favorites/{favorite['id']}/{action}", json=body)
            assert response.status_code == 404
            assert "Título privado" not in response.text and "a001" not in response.text
        detail = other.get("/api/favorites/" + favorite["id"])
        assert detail.status_code == 404 and "Título privado" not in detail.text


@pytest.mark.parametrize("protection", ["csrf", "origin", "expired"])
def test_favorite_mutations_require_live_session_origin_and_csrf(
    manager_client: TestClient, db: Session, protection: str
) -> None:
    answer = ask(manager_client)
    favorite = save(manager_client, answer["id"])
    if protection == "csrf":
        manager_client.headers["X-CSRF-Token"] = "invalid"
    elif protection == "origin":
        manager_client.headers["Origin"] = "https://untrusted.invalid"
    else:
        for session in db.scalars(select(LoginSession)):
            session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    expected = 401 if protection == "expired" else 403
    for path, body in (
        ("/api/favorites", {"answer_id": answer["id"], "name": "Nome"}),
        (f"/api/favorites/{favorite['id']}/rename", {"name": "Nome", "revision": 1}),
        (f"/api/favorites/{favorite['id']}/delete", {"revision": 1}),
        (f"/api/favorites/{favorite['id']}/run", {"revision": 1}),
    ):
        response = manager_client.post(path, json=body)
        assert response.status_code == expected and "3000" not in response.text
    record = db.get(FavoriteRecord, favorite["id"])
    assert record is not None and record.revision == 1
    if protection == "expired":
        assert manager_client.get("/api/favorites").status_code == 401


def test_revocation_hides_title_and_plan_and_blocks_all_actions(
    manager_client: TestClient, db: Session
) -> None:
    answer = ask(manager_client)
    favorite = save(manager_client, answer["id"], "Receita privada da Centro")
    db.execute(delete(StorePermission).where(StorePermission.user_id == "manager_a"))
    db.commit()
    listed = manager_client.get("/api/favorites")
    assert listed.status_code == 200 and listed.json() == []
    for path, body in (
        (f"/api/favorites/{favorite['id']}/rename", {"name": "Nome", "revision": 1}),
        (f"/api/favorites/{favorite['id']}/delete", {"revision": 1}),
        (f"/api/favorites/{favorite['id']}/run", {"revision": 1}),
        ("/api/favorites", {"answer_id": answer["id"], "name": "Nome"}),
    ):
        response = manager_client.post(path, json=body)
        assert response.status_code == 403
        assert "Centro" not in response.text and "a001" not in response.text
    detail = manager_client.get("/api/favorites/" + favorite["id"])
    assert detail.status_code == 403 and "Centro" not in detail.text


@pytest.mark.parametrize("tampering", ["schema", "period", "scope_name", "empty_scope", "scope"])
def test_saved_plan_and_schema_are_revalidated_without_leaking_titles(
    manager_client: TestClient, db: Session, tampering: str
) -> None:
    favorite = save(manager_client, ask(manager_client)["id"], "Título protegido")
    record = db.get(FavoriteRecord, favorite["id"])
    assert record is not None
    plan = dict(record.plan)
    if tampering == "schema":
        record.schema_version = 99
    elif tampering == "period":
        plan["period"] = {"start": "2026-01-01", "end": "2026-08-17"}
    else:
        plan["store_references"] = (
            []
            if tampering == "empty_scope"
            else ["Centro"]
            if tampering == "scope_name"
            else ["b001"]
        )
    record.plan = plan
    db.commit()
    assert manager_client.get("/api/favorites").json() == []
    for response in (
        manager_client.get("/api/favorites/" + favorite["id"]),
        manager_client.post(f"/api/favorites/{favorite['id']}/run", json={"revision": 1}),
    ):
        assert response.status_code == (409 if tampering in ("schema", "period") else 403)
        assert "Título protegido" not in response.text and "b001" not in response.text


def test_favorite_source_fk_cannot_reference_another_owner(
    manager_client: TestClient, db: Session
) -> None:
    answer = ask(manager_client)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            FavoriteRecord(
                tenant_id="org_a",
                user_id="supervisor_a",
                source_answer_id=answer["id"],
                name="Tentativa",
                plan=answer["plan"],
            )
        )
        db.flush()


def test_unexecuted_answers_and_client_plans_cannot_be_saved(manager_client: TestClient) -> None:
    answer = ask(manager_client, "Qual o lucro ontem?")
    response = manager_client.post(
        "/api/favorites", json={"answer_id": answer["id"], "name": "Sem cálculo"}
    )
    assert response.status_code == 422
    assert (
        manager_client.post(
            "/api/favorites", json={"answer_id": answer["id"], "name": "Nome", "plan": {}}
        ).status_code
        == 422
    )


def test_run_is_deterministic_persists_a_new_result_and_keeps_history_immutable(
    manager_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from loja_assistente.assistant import service as assistant_service

    source = ask(manager_client)
    favorite = save(manager_client, source["id"])
    item = db.get(OrderItem, ("org_a", "oa4-item-0"))
    dataset = db.get(Dataset, "manual-v1")
    assert item is not None and dataset is not None
    item.unit_price_cents = 9_007_199_254_740_993
    dataset.version = "manual-v2"
    db.commit()
    interpret = Mock(side_effect=AssertionError("Um favorito não interpreta nem chama o provedor"))
    monkeypatch.setattr(assistant_service, "interpret_request", interpret)
    monkeypatch.setattr(assistant_service.demo, "interpret", interpret)
    monkeypatch.setattr(assistant_service.openai_adapter, "interpret", interpret)
    response = manager_client.post(f"/api/favorites/{favorite['id']}/run", json={"revision": 1})
    assert response.status_code == 200, response.text
    current = response.json()
    assert current["id"] != source["id"] and current["request_id"] != source["request_id"]
    assert current["conversation_id"] != source["conversation_id"]
    assert current["plan"] == favorite["plan"]
    assert current["result"]["value"] == "9007199254742993"
    assert current["result"]["totals"]["revenue_cents"] == "9007199254742993"
    assert current["result"]["dataset_version"] == "manual-v2"
    assert current["result"]["request_id"] == current["request_id"]
    assert manager_client.get("/api/answers/" + current["id"]).json() == current
    assert manager_client.get("/api/answers/" + source["id"]).json() == source
    refreshed = manager_client.get("/api/favorites").json()[0]
    assert refreshed["revision"] == 2 and refreshed["source_answer_id"] == source["id"]
    assert (
        manager_client.post(
            f"/api/favorites/{favorite['id']}/run", json={"revision": 1}
        ).status_code
        == 409
    )
    interpret.assert_not_called()


@pytest.mark.parametrize("coverage", ["partial", "absent"])
def test_run_preserves_coverage_semantics(
    supervisor_client: TestClient, db: Session, coverage: str
) -> None:
    source = ask(supervisor_client)
    favorite = save(supervisor_client, source["id"])
    removal = delete(Coverage).where(
        Coverage.tenant_id == "org_a", Coverage.date == date(2026, 8, 16)
    )
    if coverage == "partial":
        removal = removal.where(Coverage.store_id == "a002")
    db.execute(removal)
    db.commit()
    response = supervisor_client.post(f"/api/favorites/{favorite['id']}/run", json={"revision": 1})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["result"]["coverage"]["status"] == coverage
    assert answer["result"]["value"] == ("3000" if coverage == "partial" else None)
    assert answer["status"] == ("ready" if coverage == "partial" else "no_data")
    assert supervisor_client.get("/api/answers/" + source["id"]).json() == source


def test_empty_legacy_scope_is_frozen_to_the_original_result(
    manager_client: TestClient, db: Session
) -> None:
    source = ask(manager_client)
    record = db.get(AnswerRecord, source["id"])
    assert record is not None
    payload = dict(record.payload)
    payload["plan"] = {**payload["plan"], "store_references": []}
    record.payload = payload
    db.add(StorePermission(tenant_id="org_a", user_id="manager_a", store_id="a002"))
    db.commit()
    favorite = save(manager_client, source["id"])
    assert favorite["plan"]["store_references"] == ["a001"]
    run = manager_client.post(f"/api/favorites/{favorite['id']}/run", json={"revision": 1})
    assert run.json()["result"]["value"] == "3000"


def test_html_name_is_data_and_never_used_as_interpretation(manager_client: TestClient) -> None:
    hostile = '<img src=x onerror="alert(1)">'
    favorite = save(manager_client, ask(manager_client)["id"], hostile)
    assert favorite["name"] == hostile
    current = manager_client.post(f"/api/favorites/{favorite['id']}/run", json={"revision": 1})
    assert current.status_code == 200 and current.json()["result"]["value"] == "3000"


def test_list_is_bounded(manager_client: TestClient, db: Session) -> None:
    source = ask(manager_client)
    for index in range(55):
        answer_id = f"bounded-answer-{index}"
        payload = {**source, "id": answer_id}
        db.add(
            AnswerRecord(
                id=answer_id,
                tenant_id="org_a",
                user_id="manager_a",
                conversation_id=source["conversation_id"],
                payload=payload,
            )
        )
        db.flush()
        db.add(
            FavoriteRecord(
                tenant_id="org_a",
                user_id="manager_a",
                source_answer_id=answer_id,
                name=f"Favorito {index}",
                plan=source["plan"],
            )
        )
    db.commit()
    assert len(manager_client.get("/api/favorites").json()) == 50


def test_two_independent_connections_cannot_run_the_same_revision(
    manager_client: TestClient,
    db: Session,
    test_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    favorite = save(manager_client, ask(manager_client)["id"])
    before = db.scalar(select(func.count()).select_from(AnswerRecord))
    locked, release = Event(), Event()
    execute = service.execute_query

    def delayed_query(*args: Any, **kwargs: Any) -> Any:
        locked.set()
        if not release.wait(timeout=10):
            raise AssertionError("O teste não liberou a consulta concorrente")
        return execute(*args, **kwargs)

    monkeypatch.setattr(service, "execute_query", delayed_query)

    def first_run() -> AnswerRecord | str:
        with Session(test_engine) as first:
            return service.run_favorite(
                first, principal(), favorite["id"], FavoriteRevisionRequest(revision=1), "first-run"
            ).id

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(first_run)
        try:
            assert locked.wait(timeout=10), "A primeira conexão não adquiriu o lock"
            with Session(test_engine) as second:
                with pytest.raises(HTTPException) as occupied:
                    service.run_favorite(
                        second,
                        principal(),
                        favorite["id"],
                        FavoriteRevisionRequest(revision=1),
                        "second-run",
                    )
                assert occupied.value.status_code == 409
        finally:
            release.set()
        answer_id = future.result(timeout=10)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AnswerRecord)) == before + 1
    assert db.get(AnswerRecord, answer_id) is not None
    with Session(test_engine) as stale:
        with pytest.raises(HTTPException) as outdated:
            service.run_favorite(
                stale, principal(), favorite["id"], FavoriteRevisionRequest(revision=1), "stale-run"
            )
        assert outdated.value.status_code == 409
    with Session(test_engine) as fresh:
        renamed = service.rename_favorite(
            fresh,
            principal(),
            favorite["id"],
            RenameFavoriteRequest(name="Depois da execução", revision=2),
        )
        assert renamed.revision == 3
