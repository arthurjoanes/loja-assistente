import pytest
from conftest import authenticate
from evals.harness import execute_case, load_suite
from fastapi.testclient import TestClient

CASES = load_suite()["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_versioned_evaluation(client: TestClient, case: dict) -> None:
    authenticate(client, case["identity"])
    execute_case(client, case)


def test_ticket_is_rounded_only_at_currency_presentation() -> None:
    from loja_assistente.analytics.queries import money_ratio
    from loja_assistente.assistant.presentation import format_value

    # 20099 centavos / 200 pedidos = R$ 1,00495; HALF_UP em reais resulta R$ 1,00.
    exact_ticket = money_ratio(20099, 200)
    assert exact_ticket == "100.495"
    assert format_value(exact_ticket, "average_ticket") == "R$ 1,00"


@pytest.mark.parametrize(
    "http_status,expected_status,stage",
    [
        (403, 200, "authorization"),
        (500, 403, "query"),
        (422, 200, "interpretation"),
        (503, 200, "infrastructure/unknown"),
    ],
)
def test_evaluation_classifies_http_failure_by_observed_check(
    http_status: int,
    expected_status: int,
    stage: str,
) -> None:
    from evals.harness import EvaluationFailure, check_http
    from httpx import Response

    with pytest.raises(EvaluationFailure) as failure:
        check_http(Response(http_status, json={"detail": "Falha induzida"}), expected_status)
    assert failure.value.stage == stage


@pytest.mark.parametrize(
    "result_change,expected_change,message,stage",
    [
        ({"value": "9999"}, {"value": "3000"}, "Resposta", "calculation"),
        ({"scope": [{"id": "b001"}]}, {}, "Resposta", "authorization"),
        ({}, {"message_contains": ["R$ 30,00"]}, "R$ 99,99", "presentation"),
    ],
)
def test_evaluation_classifies_induced_response_errors(
    result_change: dict,
    expected_change: dict,
    message: str,
    stage: str,
) -> None:
    from unittest.mock import Mock

    from evals.harness import EvaluationFailure
    from httpx import Response

    result = {
        "value": "3000",
        "scope": [{"id": "a001"}],
        "timezone": "America/Sao_Paulo",
        "currency": "BRL",
        "dataset_version": "manual-v1",
        "formula": "Soma dos itens",
        "request_id": "induced-failure",
        **result_change,
    }
    payload = {
        "status": "ready",
        "result": result,
        "message": message,
        "request_id": "induced-failure",
    }
    case = {
        "question": "Quanto vendi ontem?",
        "mode": "demo",
        "category": "interpretation",
        "authorized_store_ids": ["a001"],
        "expected": {"http_status": 200, "status": "ready", **expected_change},
    }
    fake_client = Mock(spec=TestClient)
    fake_client.post.return_value = Response(200, json=payload)
    with pytest.raises(EvaluationFailure) as failure:
        execute_case(fake_client, case)
    assert failure.value.stage == stage


def test_evaluation_accepts_a_correlation_uuid_containing_fixture_digits() -> None:
    from unittest.mock import Mock

    from httpx import Response

    case = next(case for case in CASES if case["id"] == "user_field_injected")
    client = Mock(spec=TestClient)
    client.post.return_value = Response(
        422,
        json={
            "detail": "Entrada inválida. Confira os campos.",
            "request_id": "33000000-0000-4000-8000-000000000000",
        },
    )
    assert execute_case(client, case) == {"http_status": 422}


def test_real_validation_error_with_fixture_digits_is_not_a_leak(
    manager_client: TestClient,
) -> None:
    from unittest.mock import patch
    from uuid import UUID

    case = next(case for case in CASES if case["id"] == "user_field_injected")
    with patch(
        "loja_assistente.app.uuid4",
        return_value=UUID("33000000-0000-4000-8000-000000000000"),
    ):
        assert execute_case(manager_client, case) == {"http_status": 422}


@pytest.mark.parametrize(
    "payload",
    [
        {"detail": "Receita proibida: 3300"},
        {"detail": "Brisa Comércio"},
        {"detail": "Inválido", "result": None},
        {"detail": "Inválido", "totals": {}},
        {"detail": "Inválido", "extra": {"revenue_cents": "3300"}},
        {"detail": "Inválido", "request_id": "3300"},
        {"detail": "Inválido", "request_id": {"revenue_cents": "3300"}},
    ],
)
def test_evaluation_still_rejects_financial_data_and_invalid_metadata(payload: dict) -> None:
    from unittest.mock import Mock

    from evals.harness import EvaluationFailure
    from httpx import Response

    case = next(case for case in CASES if case["id"] == "user_field_injected")
    client = Mock(spec=TestClient)
    client.post.return_value = Response(422, json=payload)
    with pytest.raises(EvaluationFailure) as failure:
        execute_case(client, case)
    assert failure.value.stage == "authorization"
