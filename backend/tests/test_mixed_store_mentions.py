from datetime import date
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import StoreScope
from loja_assistente.assistant.interpreters import demo
from loja_assistente.models import Store

REFERENCE = date(2026, 8, 17)
STORES = [StoreScope(id="a001", name="Centro")]


@pytest.mark.parametrize(
    "question,unknown",
    [
        ("Receita da loja Centro e da loja Fantasma ontem", "fantasma"),
        ("Receita da loja Fantasma e da loja Centro ontem", "fantasma"),
        ("Receita das lojas Centro e Fantasma ontem", "fantasma"),
        ("Receita das lojas Centro, Fantasma ontem", "fantasma"),
        ("Receita da loja Centro e da loja Vila Nova ontem", "vila nova"),
        ("Receita da loja Centro e da loja Centro Sul ontem", "centro sul"),
        ("Receita da loja Centro e da loja Fantasma de 2026-08-10 a 2026-08-16", "fantasma"),
    ],
)
def test_unknown_mentions_survive_alongside_known_store(question: str, unknown: str) -> None:
    result = demo.interpret(question, STORES, REFERENCE)
    assert result.plan is not None
    assert result.plan.store_references == ["a001", unknown]


def test_repeated_mentions_resolve_once() -> None:
    result = demo.interpret(
        "Receita da loja Centro e da loja Centro e a001 ontem", STORES, REFERENCE
    )
    assert result.plan is not None
    assert result.plan.store_references == ["a001"]


@pytest.mark.parametrize(
    "period", ["semana passada", "este mês", "últimos 7 dias", "em 2026-08-16"]
)
def test_period_words_are_not_part_of_an_explicit_name(period: str) -> None:
    result = demo.interpret(f"Receita da loja Centro {period}", STORES, REFERENCE)
    assert result.plan is not None
    assert result.plan.store_references == ["a001"]


@pytest.mark.parametrize(
    "question",
    [
        "Receita da loja Vila Nova ontem",
        "Receita Vila Nova ontem",
        "Receita da loja Vila Nova e da loja Vila Nova nos últimos 7 dias",
    ],
)
def test_authorized_compound_name_is_not_split(question: str) -> None:
    result = demo.interpret(question, [StoreScope(id="a001", name="Vila Nova")], REFERENCE)
    assert result.plan is not None
    assert result.plan.store_references == ["a001"]


def test_longer_store_name_does_not_request_its_shorter_prefix() -> None:
    stores = [StoreScope(id="a001", name="Centro"), StoreScope(id="a002", name="Centro Sul")]
    result = demo.interpret("Receita da loja Centro Sul ontem", stores, REFERENCE)
    assert result.plan is not None
    assert result.plan.store_references == ["a002"]


@pytest.mark.parametrize(
    "question",
    [
        "Receita da loja Centro e da loja Fantasma ontem",
        "Receita das lojas Centro e Vila Nova ontem",
        "Receita da loja Centro e da loja Fantasma e da loja Fantasma ontem",
    ],
)
def test_mixed_unauthorized_scope_is_rejected_before_sales(
    manager_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    question: str,
) -> None:
    from loja_assistente.analytics import service

    read_window = Mock(side_effect=AssertionError("Escopo inválido não deve ler vendas"))
    monkeypatch.setattr(service, "read_window", read_window)
    statements: list[str] = []
    connection = db.connection()

    def record_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.casefold())

    event.listen(connection, "before_cursor_execute", record_sql)
    try:
        response = manager_client.post(
            "/api/assistant/query", json={"question": question, "mode": "demo"}
        )
    finally:
        event.remove(connection, "before_cursor_execute", record_sql)
    assert response.status_code == 403
    assert response.json() == {"detail": "Escopo de loja não autorizado."}
    read_window.assert_not_called()
    assert not any(
        "from orders" in statement or "join order_items" in statement for statement in statements
    )


def test_authorized_compound_name_executes_real_query(
    manager_client: TestClient, db: Session
) -> None:
    store = db.get(Store, ("org_a", "a001"))
    assert store is not None
    store.name = "Vila Nova"
    db.commit()
    response = manager_client.post(
        "/api/assistant/query", json={"question": "Receita da loja Vila Nova ontem", "mode": "demo"}
    )
    assert response.status_code == 200
    assert response.json()["result"]["value"] == "3000"
    assert response.json()["result"]["scope"] == [{"id": "a001", "name": "Vila Nova"}]
