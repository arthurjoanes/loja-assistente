from itertools import combinations

import pytest
from fastapi.testclient import TestClient
from manual_fixture import IDENTITIES, PASSWORD
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "   \n\t"},
        {"question": "\u00a0"},
        {"question": "x" * 1001},
        {"question": 42},
        {"mode": ""},
        {"mode": "other"},
        {"mode": None},
        {"store_ids": [""]},
        {"store_ids": [" "]},
        {"store_ids": ["a" * 65]},
        {"store_ids": ["a001"] * 7},
        {"conversation_id": "x" * 37},
        {"tenant_id": "org_b"},
        {"period": {"start": "2026-08-17", "end": "2026-08-16"}},
        {"period": {"start": "2026-08-17", "end": "2026-08-17"}},
        {"period": {"start": "2026-02-29", "end": "2026-03-01"}},
        {"period": {"start": "0000-01-01", "end": "0000-01-02"}},
        {"period": {"start": "2026-05-18", "end": "2026-08-17"}},
    ],
)
def test_invalid_request_fields_never_reach_analytics(
    payload: dict, manager_client: TestClient, db: Session
) -> None:
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())

    connection = db.connection()
    event.listen(connection, "before_cursor_execute", record)
    try:
        response = manager_client.post(
            "/api/assistant/query", json={"question": "Receita ontem", "mode": "demo", **payload}
        )
    finally:
        event.remove(connection, "before_cursor_execute", record)
    assert response.status_code == 422
    assert not any("from orders" in sql or "join order_items" in sql for sql in statements)


@pytest.mark.parametrize(
    "left,right", list(combinations(["receita", "pedidos", "ticket medio", "unidades"], 2))
)
@pytest.mark.parametrize("connector", ["e", "por"])
def test_metric_combinations_are_not_silently_reduced(
    left: str,
    right: str,
    connector: str,
    manager_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from loja_assistente.assistant import service

    def forbidden_query(*_args):
        pytest.fail("Ambiguous metrics must never read sales")

    monkeypatch.setattr(service, "execute_query", forbidden_query)
    response = manager_client.post(
        "/api/assistant/query", json={"question": f"{left} {connector} {right} ontem"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["plan"] is None
    assert response.json()["result"] is None


@pytest.mark.parametrize(
    "question,metric,value",
    [
        ("  QuAL   A  RECEITA  LÍQUIDA\n ONTEM?  ", "revenue", "3000"),
        ("Qual o TÍQUETE médio ontem?", "average_ticket", "1500.00"),
        ("Qual a quantidade de pedidos ontem?", "orders", "2"),
        ("Quantas unidades vendi ontem?", "units", "8"),
    ],
)
def test_spaces_accents_and_explicit_metrics_keep_manual_oracle(
    question: str, metric: str, value: str, manager_client: TestClient
) -> None:
    response = manager_client.post(
        "/api/assistant/query", json={"question": question, "store_ids": ["a001", "a001"]}
    )
    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] == "ready"
    assert answer["plan"]["metric"] == metric
    assert answer["plan"]["store_references"] == ["a001"]
    assert answer["result"]["value"] == value
    assert answer["question"] == question.strip()


@pytest.mark.parametrize(
    "question",
    [
        "Qual foi o ticket e a quantidade de pedidos ontem?",
        "Receita ontem anterior",
        "Ranking 2 top 3 produtos por receita ontem",
        "Receita dos ultimos 7 dias e dos ultimos 30 dias",
        "Receita de 9999-12-31",
        "Compare receita de 0001-01-01 com o periodo anterior",
    ],
)
def test_extreme_and_ambiguous_text_requests_are_safe(
    question: str, manager_client: TestClient
) -> None:
    response = manager_client.post("/api/assistant/query", json={"question": question})
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["result"] is None


@pytest.mark.parametrize(
    "password,status",
    [("", 422), (" ", 401), (PASSWORD + " ", 401), ("x" * 200, 401), ("x" * 201, 422)],
)
def test_password_boundaries_are_exact(password: str, status: int, client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": IDENTITIES["manager_a"], "password": password}
    )
    assert response.status_code == status
    assert "la_session" not in response.cookies


def test_email_case_and_surrounding_spaces_do_not_change_identity(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "  " + IDENTITIES["manager_a"].upper() + "  ", "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] == "manager_a"


def test_question_limit_is_inclusive_and_unknown_store_is_not_ignored(
    manager_client: TestClient,
) -> None:
    assert (
        manager_client.post("/api/assistant/query", json={"question": "x" * 1000}).status_code
        == 200
    )
    forbidden = manager_client.post(
        "/api/assistant/query", json={"question": "Receita ontem", "store_ids": ["a001", "b001"]}
    )
    assert forbidden.status_code == 403


@pytest.mark.parametrize(
    "email,status",
    [
        ("", 422),
        ("aa", 422),
        ("   ", 401),
        ("x" * 254, 401),
        ("x" * 255, 422),
        (42, 422),
        (None, 422),
    ],
)
def test_login_email_boundaries_do_not_create_sessions(
    email: object, status: int, client: TestClient
) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == status
    assert "la_session" not in response.cookies
