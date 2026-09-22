from datetime import date
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import StoreScope
from loja_assistente.assistant.interpreters import demo

UNSUPPORTED_QUESTIONS = [
    "Receita ontem das 10 às 14",
    "Receita ontem entre 10 e 14",
    "Receita diária e ranking de produtos ontem",
    "Pedidos e unidades ontem",
    "Quanto vendi ontem somente em dinheiro?",
    "Receita no cartão ontem",
    "Receita de Pix ontem",
    "Receita por vendedor ontem",
    "Receita por categoria ontem",
    "Receita do produto Caneca ontem",
    "Receita de canecas ontem",
    "Receita do canal online ontem",
    "Receita ontem exceto os pedidos de Maria",
    "Receita ontem sem canecas",
    "Receita apenas da manhã ontem",
    "Receita entre 10h e 14h ontem",
    "Receita às 10:30 ontem",
    "Receita ontem acima de 100 reais",
    "Receita ontem ou hoje",
    "Receita de 2026-08-15 até ontem",
    "Receita e unidades ontem",
    "Receita líquida promocional ontem",
]


@pytest.mark.parametrize("question", UNSUPPORTED_QUESTIONS)
def test_unrepresented_filter_never_returns_general_total(
    question: str, manager_client: TestClient, db: Session
) -> None:
    statements: list[str] = []
    connection = db.connection()

    def record_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.casefold())

    event.listen(connection, "before_cursor_execute", record_sql)
    try:
        response = manager_client.post(
            "/api/assistant/query", json={"question": question, "mode": "demo"}
        )
    finally:
        event.remove(connection, "before_cursor_execute", record_sql)
    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] in ("needs_clarification", "unsupported")
    assert answer["result"] is None and answer["plan"] is None
    assert not any("from orders" in sql or "join order_items" in sql for sql in statements)


@pytest.mark.parametrize(
    "question", ["Receita em dinheiro ontem", "Receita por vendedor ontem", "Receita às 10h ontem"]
)
def test_explicit_unsupported_dimensions_are_blocked_before_llm(
    question: str, manager_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from loja_assistente.assistant import service
    from loja_assistente.config import settings

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "contract-only-not-a-real-key")
    provider = Mock(side_effect=AssertionError("Não deve chamar um provedor pago"))
    query = Mock(side_effect=AssertionError("Não deve consultar o total geral"))
    from loja_assistente.assistant import interpretation

    monkeypatch.setattr(interpretation, "OpenAI", provider)
    monkeypatch.setattr(service, "execute_query", query)
    response = manager_client.post(
        "/api/assistant/query", json={"question": question, "mode": "llm"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"
    assert response.json()["result"] is None
    provider.assert_not_called()
    query.assert_not_called()


def test_explicit_ranking_metric_overrides_conventional_most_sold_wording() -> None:
    interpretation = demo.interpret(
        "Quais os 5 produtos mais vendidos por receita ontem?",
        [StoreScope(id="a001", name="Centro")],
        date(2026, 8, 17),
    )
    assert interpretation.plan is not None
    assert interpretation.plan.intent == "ranking"
    assert interpretation.plan.metric == "revenue"


@pytest.mark.parametrize(
    "question",
    [
        "Qual a receita líquida de ontem?",
        "Ranking dos produtos por receita ontem",
        "Quantas unidades vendemos ontem?",
        "Qual foi a receita da minha loja ontem?",
    ],
)
def test_documented_metric_without_extra_filters_remains_supported(question: str) -> None:
    interpretation = demo.interpret(
        question, [StoreScope(id="a001", name="Centro")], date(2026, 8, 17)
    )
    assert interpretation.status == "ready", interpretation.message
