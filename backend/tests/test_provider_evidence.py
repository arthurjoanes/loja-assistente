import json
from dataclasses import asdict
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from openai.types.shared import ReasoningEffort
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.orm import Session
from test_interpreters import PLAN, response_body

from loja_assistente.analytics.contracts import StoreScope
from loja_assistente.assistant.interpreters import demo, openai_adapter
from loja_assistente.assistant.provider_trace import EvaluationHooks, observe_provider
from loja_assistente.config import Settings


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.openai.azure.com/openai/v1/",
        "https://example.services.ai.azure.com/openai/v1/",
        "https://api.openai.com/v1/",
    ],
)
def test_v1_inference_endpoint(endpoint: str) -> None:
    assert Settings(demo_mode=True, openai_base_url=endpoint).openai_base_url == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.services.ai.azure.com/api/projects/my-project",
        "http://example.openai.azure.com/openai/v1/",
        "https://example.openai.azure.com/openai/v1/?api-version=2025-01-01",
        "https://secret@example.openai.azure.com/openai/v1/",
        "https://evil.test/openai/v1/",
    ],
)
def test_configuration_does_not_send_key_to_project_or_arbitrary_endpoint(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        Settings(demo_mode=True, openai_base_url=endpoint)


@pytest.mark.parametrize("reasoning_effort", [None, "none"])
def test_provider_trace_is_measured_and_sanitized(reasoning_effort: ReasoningEffort | None) -> None:
    records = []
    reservations = []
    payload = response_body(
        {
            "type": "output_text",
            "text": json.dumps({"status": "ready", "plan": PLAN, "message": ""}),
            "annotations": [],
        }
    )
    payload["usage"] = {"input_tokens": 181, "output_tokens": 72, "total_tokens": 253}

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://my-resource.openai.azure.com/openai/v1/responses"
        body = json.loads(request.content)
        assert body["model"] == "my-deployment"
        assert body["max_output_tokens"] == 1000 and body["store"] is False
        assert body["text"]["format"]["strict"] is True
        schema = body["text"]["format"]["schema"]
        assert schema["required"] == list(schema["properties"])
        assert schema["$defs"]["QueryPlan"]["required"] == list(
            schema["$defs"]["QueryPlan"]["properties"]
        )
        for keyword in ("maxLength", "maxItems", "minimum", "maximum", "format", "default"):
            assert f'"{keyword}":' not in json.dumps(schema)
        if reasoning_effort is None:
            assert "reasoning" not in body
        else:
            assert body["reasoning"] == {"effort": reasoning_effort}
        return httpx.Response(200, json=payload, headers={"x-request-id": "provider-proof-id"})

    with (
        OpenAI(
            api_key="never-log-this-secret",
            base_url="https://my-resource.openai.azure.com/openai/v1/",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        ) as client,
        observe_provider(
            EvaluationHooks(
                reserve=lambda *args: reservations.append(args),
                record=records.append,
            )
        ),
    ):
        interpreted = openai_adapter.interpret(
            "Quanto eu vendi ontem?",
            [StoreScope(id="a001", name="Centro")],
            date(2026, 8, 17),
            client=client,
            model="my-deployment",
            reasoning_effort=reasoning_effort,
        )
    assert interpreted.plan is not None and interpreted.plan.metric == "revenue"
    assert len(records) == len(reservations) == 1
    trace = asdict(records[0])
    assert trace["provider_request_id"] == "provider-proof-id"
    assert trace["input_tokens"] == 181 and trace["output_tokens"] == 72
    assert trace["status"] == "completed" and trace["attempts"] == 1
    assert trace["reasoning_effort"] == reasoning_effort
    assert reservations[0][1] > 181 and reservations[0][2] == 1000
    assert "never-log-this-secret" not in json.dumps(trace)
    assert "Quanto eu" not in json.dumps(trace)


def test_reasoning_configuration_preserves_omission_and_rejects_invalid_effort() -> None:
    assert Settings(demo_mode=True, openai_reasoning_effort="").openai_reasoning_effort is None
    assert (
        Settings(demo_mode=True, openai_reasoning_effort="none").openai_reasoning_effort == "none"
    )
    with pytest.raises(ValidationError):
        Settings(demo_mode=True, openai_reasoning_effort="unbounded")


def test_budget_rejection_happens_before_any_network_attempt() -> None:
    calls = []
    records = []

    def reject(*_args: object) -> None:
        raise RuntimeError("Budget exhausted")

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("No network after budget refusal")

    with (
        OpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.Client(
                transport=httpx.MockTransport(handle),
            ),
        ) as client,
        observe_provider(EvaluationHooks(reserve=reject, record=records.append)),
    ):
        with pytest.raises(RuntimeError, match="Budget"):
            openai_adapter.interpret(
                "Receita ontem", [], date(2026, 8, 17), client=client, model="test"
            )
    assert calls == records == []


def test_invalid_schema_still_records_provider_usage_and_correlation() -> None:
    records = []
    payload = response_body(
        {"type": "output_text", "text": '{"sql":"forbidden"}', "annotations": []}
    )
    payload["usage"] = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}
    with (
        OpenAI(
            api_key="test",
            max_retries=0,
            http_client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200, json=payload, headers={"apim-request-id": "azure-test-id"}
                    ),
                )
            ),
        ) as client,
        observe_provider(EvaluationHooks(reserve=lambda *_args: None, record=records.append)),
    ):
        with pytest.raises(openai_adapter.ProviderUnavailable, match="inválido"):
            openai_adapter.interpret(
                "Receita ontem", [], date(2026, 8, 17), client=client, model="test"
            )
    assert records[0].status == "invalid_output"
    assert records[0].total_tokens == 110
    assert records[0].provider_request_id == "azure-test-id"


@pytest.mark.parametrize(
    "invalid_plan",
    [{**PLAN, "limit": 21}, {**PLAN, "period": {"start": "invalid", "end": "2026-08-17"}}],
)
def test_transport_subset_does_not_weaken_domain_validation(invalid_plan: dict) -> None:
    payload = response_body(
        {
            "type": "output_text",
            "text": json.dumps({"status": "ready", "plan": invalid_plan, "message": ""}),
            "annotations": [],
        }
    )
    with OpenAI(
        api_key="simulated",
        max_retries=0,
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    ) as client:
        with pytest.raises(openai_adapter.ProviderUnavailable, match="inválido"):
            openai_adapter.interpret(
                "Receita ontem", [], date(2026, 8, 17), client=client, model="test"
            )


@pytest.mark.parametrize(
    "question",
    [
        "Quanto eu vendi ontem?",
        "Me mostra o faturamento de ontem",
        "Oi, qual a receita de ontem?",
        "Só queria saber a receita de ontem",
        "Boa tarde, receita de ontem",
    ],
)
def test_conversational_prefix_does_not_become_financial_filter(question: str) -> None:
    result = demo.interpret(question, [StoreScope(id="a001", name="Centro")], date(2026, 8, 17))
    assert result.plan is not None and result.plan.model_dump(mode="json") == PLAN


@pytest.mark.parametrize(
    "question",
    [
        "Só queria saber a receita somente em dinheiro ontem",
        "Oi, receita apenas da manhã ontem",
        "Me mostra a receita sem canecas ontem",
        "Boa tarde, receita da tarde de ontem",
    ],
)
def test_prefix_removal_preserves_unsupported_qualifiers(question: str) -> None:
    result = demo.interpret(question, [StoreScope(id="a001", name="Centro")], date(2026, 8, 17))
    assert result.plan is None and result.status == "needs_clarification"


def test_greeting_is_helpful_without_query_plan() -> None:
    result = demo.interpret("Oi!", [], date(2026, 8, 17))
    assert result.plan is None and "Qual indicador e período" in result.message


@pytest.mark.parametrize("store_id,expected_status", [("a001", 200), ("b001", 403)])
def test_provider_hooks_follow_real_http_authorization_and_calculation(
    manager_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    store_id: str,
    expected_status: int,
) -> None:
    from test_budget_adapter import ControlledBudget

    from loja_assistente.assistant import interpretation
    from loja_assistente.assistant import service as assistant_service
    from loja_assistente.config import settings

    # This older authorization/calculation test uses an uncommitted savepoint fixture.
    # Ledger durability is covered separately with committed tenants and sessions.
    monkeypatch.setattr(assistant_service, "DurableBudget", lambda *_args: ControlledBudget([]))

    records = []
    reservations = []
    statements = []
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "simulated-contract-only")
    payload = response_body(
        {
            "type": "output_text",
            "text": json.dumps(
                {
                    "status": "ready",
                    "plan": {**PLAN, "store_references": [store_id]},
                    "message": "",
                }
            ),
            "annotations": [],
        }
    )

    def client_factory(**kwargs):
        return OpenAI(
            **kwargs,
            http_client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200, json=payload, headers={"x-request-id": "simulated-http-proof"}
                    ),
                )
            ),
        )

    def inspect_sql(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement.casefold())

    monkeypatch.setattr(interpretation, "OpenAI", client_factory)
    connection = db.connection()
    event.listen(connection, "before_cursor_execute", inspect_sql)
    try:
        with observe_provider(
            EvaluationHooks(reserve=lambda *args: reservations.append(args), record=records.append)
        ):
            response = manager_client.post(
                "/api/assistant/query", json={"question": "Quanto eu vendi ontem?", "mode": "llm"}
            )
    finally:
        event.remove(connection, "before_cursor_execute", inspect_sql)
    assert response.status_code == expected_status
    assert len(reservations) == len(records) == 1
    assert records[0].provider_request_id == "simulated-http-proof"
    if expected_status == 200:
        result = response.json()["result"]
        assert result["totals"] == {
            "revenue_cents": "3000",
            "orders": 2,
            "units": 8,
            "average_ticket_cents": "1500.00",
        }
        evidence = manager_client.get(f"/api/answers/{response.json()['id']}/evidence")
        assert evidence.json() == result
    else:
        assert "result" not in response.json() and "3300" not in response.text
        assert not any("from orders" in sql or "join order_items" in sql for sql in statements)
