from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from loja_assistente.analytics.contracts import Period, QueryPlan, StoreScope
from loja_assistente.assistant.contracts import Answer, DemoInterpretation, Interpretation
from loja_assistente.assistant.interpreters import demo, openai_adapter
from loja_assistente.clarifications.contracts import (
    ClarificationChoice,
    ClarificationResponse,
    PartialPlan,
    PendingClarification,
)
from loja_assistente.clarifications.state import period_choices

REFERENCE = date(2026, 8, 17)
STORES = [StoreScope(id="a001", name="Centro"), StoreScope(id="a002", name="Jardins")]


def partial() -> PartialPlan:
    return PartialPlan(intent="aggregate", metric="revenue", store_ids=["a001"])


def pending() -> PendingClarification:
    now = datetime.now(UTC)
    return PendingClarification(
        id="pending",
        revision=1,
        status="pending",
        original_question="Receita da loja Centro",
        partial_plan=partial(),
        missing_field="period",
        choices=period_choices(REFERENCE),
        created_at=now,
        expires_at=now + timedelta(minutes=30),
        mode="demo",
        reference_date=REFERENCE,
    )


def test_partial_is_not_an_executable_query_plan() -> None:
    value = partial()
    with pytest.raises(ValueError, match="precisa"):
        value.executable()
    with pytest.raises(ValidationError):
        QueryPlan.model_validate(value.model_dump())
    complete = PartialPlan.model_validate(
        {**value.model_dump(), "period": {"start": "2026-08-16", "end": "2026-08-17"}}
    )
    assert complete.executable().store_references == ["a001"]


@pytest.mark.parametrize(
    "update",
    [
        {"intent": "ranking", "metric": "orders"},
        {"limit": 21},
        {"limit": "5"},
        {"grouping": "day"},
        {"store_ids": ["a001", "a001"]},
        {"store_ids": [""]},
        {"sql": "select * from orders"},
        {"tenant_id": "org_b"},
    ],
)
def test_partial_still_validates_supported_domain_fields(update: dict) -> None:
    with pytest.raises(ValidationError):
        PartialPlan.model_validate({**partial().model_dump(), **update})


def test_missing_period_conserves_metric_and_explicit_store() -> None:
    value = demo.interpret("Receita da loja Centro", STORES, REFERENCE, store_ids=["a002"])
    assert isinstance(value, DemoInterpretation)
    assert value.clarification is not None
    assert value.plan is None and value.status == "needs_clarification"
    assert value.clarification.partial_plan.metric == "revenue"
    assert value.clarification.partial_plan.store_ids == ["a001"]
    assert value.clarification.partial_plan.period is None


def test_omitting_store_keeps_all_authorized_stores() -> None:
    value = demo.interpret("Quanto vendi ontem?", STORES, REFERENCE)
    assert value.status == "ready" and value.plan is not None
    assert value.plan.store_references == ["a001", "a002"]
    missing = demo.interpret("Quanto vendi?", STORES, REFERENCE)
    assert isinstance(missing, DemoInterpretation) and missing.clarification is not None
    assert missing.clarification.missing_field == "period"
    assert missing.clarification.partial_plan.store_ids == ["a001", "a002"]


def test_real_duplicate_names_offer_clear_ids_and_preserve_text_period() -> None:
    value = demo.interpret(
        "Unidades da loja Centro ontem",
        [STORES[0], StoreScope(id="a002", name="Centro")],
        REFERENCE,
        period=Period(start=date(2026, 8, 10), end=REFERENCE),
    )
    assert isinstance(value, DemoInterpretation) and value.clarification is not None
    draft = value.clarification
    assert draft.missing_field == "store"
    assert draft.partial_plan.metric == "units"
    assert draft.partial_plan.period == Period(start=date(2026, 8, 16), end=REFERENCE)
    assert [choice.store_ids for choice in draft.choices] == [["a001"], ["a002"]]
    assert all(choice.store_ids[0] in choice.label for choice in draft.choices)


@pytest.mark.parametrize(
    "question",
    [
        "Receita da loja Centro e da loja Norte",
        "Receita da loja Centro e da loja Fantasma",
        "Receita da loja Centro e da loja b001",
    ],
)
def test_unknown_or_forbidden_mentions_never_offer_partial_choices(question: str) -> None:
    value = demo.interpret(question, [STORES[0], StoreScope(id="a002", name="Centro")], REFERENCE)
    assert isinstance(value, DemoInterpretation)
    assert value.clarification is None and value.authorization_references
    assert value.plan is None


@pytest.mark.parametrize(
    "question",
    [
        "Receita em dinheiro",
        "Receita por vendedor",
        "Receita do produto Caneca",
        "Receita de 2026-08-20 a 2026-08-01",
        "Receita nos últimos 500 dias",
        "Receita e unidades",
        "Pedidos cancelados",
    ],
)
def test_unsupported_or_invalid_information_is_not_an_executable_slot(question: str) -> None:
    value = demo.interpret(question, STORES, REFERENCE)
    assert value.plan is None
    assert not isinstance(value, DemoInterpretation) or value.clarification is None


def test_missing_period_preserves_requested_comparison() -> None:
    value = demo.interpret("Compare receita com o período anterior", STORES, REFERENCE)
    assert isinstance(value, DemoInterpretation) and value.clarification is not None
    assert value.clarification.partial_plan.comparison == "previous_period"


def test_period_presets_are_absolute_and_end_exclusive() -> None:
    choices = period_choices(REFERENCE)
    assert [choice.id for choice in choices] == ["yesterday", "last_7_days", "last_30_days"]
    assert [choice.period.start for choice in choices] == [
        date(2026, 8, 16),
        date(2026, 8, 10),
        date(2026, 7, 18),
    ]
    assert all(choice.period.end == REFERENCE for choice in choices)


@pytest.mark.parametrize(
    "update",
    [
        {"schema_version": 2},
        {"revision": "1"},
        {"choices": [ClarificationChoice(id="store", label="Centro", store_ids=["a001"])]},
        {"expires_at": datetime.now(UTC) - timedelta(hours=1)},
        {"created_at": datetime.now()},
    ],
)
def test_pending_validates_version_revision_field_and_expiry(update: dict) -> None:
    with pytest.raises(ValidationError):
        PendingClarification.model_validate({**pending().model_dump(), **update})


def test_response_cannot_inject_plan_or_authority() -> None:
    with pytest.raises(ValidationError):
        ClarificationResponse.model_validate(
            {"pending_id": "pending", "revision": 1, "choice_id": "yesterday", "plan": {}}
        )


def test_old_answers_remain_readable_and_azure_transport_is_unchanged() -> None:
    answer = Answer(
        id="old",
        conversation_id="old-conversation",
        question="Receita",
        status="needs_clarification",
        message="Qual período?",
        mode="demo",
        plan=None,
        result=None,
        request_id="old-request",
        created_at=datetime.now(UTC),
    )
    legacy = answer.model_dump(exclude={"pending_clarification", "clarification_response"})
    assert Answer.model_validate(legacy).pending_clarification is None
    schema = openai_adapter.provider_schema()
    assert set(schema["properties"]) == {"status", "plan", "message"}
    assert set(schema["required"]) == {"status", "plan", "message"}
    assert set(Interpretation.model_json_schema()["properties"]) == {"status", "plan", "message"}
