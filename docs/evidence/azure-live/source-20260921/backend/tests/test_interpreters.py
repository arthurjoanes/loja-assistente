import json
from datetime import date

import httpx
import pytest
from openai import OpenAI

from loja_assistente.analytics.contracts import Period, QueryPlan, StoreScope
from loja_assistente.assistant.interpreters import demo, openai_adapter

STORES = [StoreScope(id="a001", name="Centro")]
REFERENCE = date(2026, 8, 17)
PLAN = {
    "intent": "aggregate",
    "metric": "revenue",
    "store_references": ["a001"],
    "period": {"start": "2026-08-16", "end": "2026-08-17"},
    "comparison": None,
    "grouping": None,
    "limit": 5,
}


def response_body(content: dict[str, object], status: str = "completed") -> dict[str, object]:
    return {
        "id": "resp_contract",
        "object": "response",
        "created_at": 1700000000,
        "model": "gpt-4.1-mini",
        "status": status,
        "output": [
            {
                "id": "msg_contract",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [content],
            }
        ],
    }


def run_adapter(payload: dict[str, object], http_status: int = 200) -> object:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["text"]["format"]["type"] == "json_schema"
        assert "única métrica principal" in body["input"][0]["content"]
        assert "password" not in request.content.decode()
        assert "b001" not in request.content.decode()
        return httpx.Response(http_status, json=payload)

    with OpenAI(
        api_key="test-contract-only",
        max_retries=0,
        timeout=12,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        return openai_adapter.interpret(
            "Receita ontem", STORES, REFERENCE, client=client, model="gpt-4.1-mini"
        )


def test_structured_success_through_real_sdk() -> None:
    payload = response_body(
        {
            "type": "output_text",
            "text": json.dumps({"status": "ready", "plan": PLAN, "message": ""}),
            "annotations": [],
        }
    )
    result = run_adapter(payload)
    assert result.plan.metric == "revenue"


@pytest.mark.parametrize(
    "extra", [{"sql": "select * from users"}, {"tenant_id": "org_b"}, {"user_id": "manager_b"}]
)
def test_model_cannot_add_authority(extra: dict[str, str]) -> None:
    payload = response_body(
        {
            "type": "output_text",
            "text": json.dumps({"status": "ready", "plan": {**PLAN, **extra}, "message": ""}),
            "annotations": [],
        }
    )
    with pytest.raises(openai_adapter.ProviderUnavailable, match="inválido"):
        run_adapter(payload)


def test_provider_refusal() -> None:
    with pytest.raises(openai_adapter.ProviderUnavailable, match="não concluiu"):
        run_adapter(response_body({"type": "refusal", "refusal": "Not supported"}))


def test_provider_incomplete() -> None:
    with pytest.raises(openai_adapter.ProviderUnavailable):
        run_adapter(
            response_body({"type": "output_text", "text": "{}", "annotations": []}, "incomplete")
        )


def test_provider_rate_limit() -> None:
    with pytest.raises(openai_adapter.ProviderUnavailable, match="Limite"):
        run_adapter(
            {"error": {"message": "test", "type": "rate_limit_error", "code": "rate_limit"}}, 429
        )


def test_provider_timeout_does_not_retry_or_fallback() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("test timeout", request=request)

    with OpenAI(
        api_key="test-only",
        max_retries=0,
        timeout=12,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        with pytest.raises(openai_adapter.ProviderUnavailable, match="Tempo limite"):
            openai_adapter.interpret(
                "Receita ontem", STORES, REFERENCE, client=client, model="gpt-4.1-mini"
            )
    assert calls == 1


def test_text_period_overrides_visual_filter() -> None:
    result = demo.interpret(
        "Receita ontem",
        STORES,
        REFERENCE,
        period=Period(start=date(2026, 8, 1), end=date(2026, 8, 8)),
    )
    assert result.plan is not None
    assert result.plan.period.start == date(2026, 8, 16)


def test_ambiguous_store_name() -> None:
    result = demo.interpret(
        "Receita Centro ontem", [*STORES, StoreScope(id="a002", name="Centro")], REFERENCE
    )
    assert result.status == "needs_clarification"


def test_continuation_keeps_metric_and_scope() -> None:
    plan = QueryPlan.model_validate(PLAN)
    result = demo.interpret("E nos sete dias anteriores?", STORES, REFERENCE, previous_plan=plan)
    assert result.plan is not None
    assert result.plan.store_references == ["a001"]
    assert result.plan.period == Period(start=date(2026, 8, 9), end=date(2026, 8, 16))


@pytest.mark.parametrize(
    "question",
    ["Receita de 2026-08-20 a 2026-08-01", "Receita nos últimos 500 dias", "Receita em 2026-02-31"],
)
def test_invalid_dates_clarify(question: str) -> None:
    assert demo.interpret(question, STORES, REFERENCE).status == "needs_clarification"
