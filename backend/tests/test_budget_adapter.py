from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APITimeoutError

from loja_assistente.assistant.budget_policy import BudgetRejected
from loja_assistente.assistant.interpreters import openai_adapter
from loja_assistente.assistant.provider_trace import EvaluationHooks, observe_provider


class ControlledBudget:
    def __init__(self, events: list[str], fail: str | None = None) -> None:
        self.events, self.fail = events, fail
        self.records = []

    def reserve(self, trace, input_units, output_units):
        self.events.append("reserve")
        assert input_units > 8192 and output_units == 1000
        if self.fail == "reserve":
            raise BudgetRejected("reservation rejected")

    def dispatch(self, call_id):
        self.events.append("dispatch-commit")
        if self.fail == "dispatch":
            raise BudgetRejected("dispatch rejected")

    def cancel_before_dispatch(self, call_id):
        self.events.append("cancel-before-dispatch")

    def record(self, trace):
        self.events.append("record")
        self.records.append(trace)
        if self.fail == "record":
            raise BudgetRejected("record failed; reservation remains")


def invoke(events: list[str], *, fail: str | None = None, network_error=None):
    def create(**kwargs):
        events.append("network")
        assert kwargs["max_output_tokens"] == 1000
        if network_error:
            raise network_error
        body = SimpleNamespace(
            id="response",
            model="unit-model",
            usage=SimpleNamespace(input_tokens=100, output_tokens=10, total_tokens=110),
            status="completed",
            output_text='{"status":"needs_clarification","plan":null,"message":"Qual período?"}',
            output=[],
        )
        return SimpleNamespace(
            headers={"x-request-id": "unit-request"},
            http_response=SimpleNamespace(
                json=lambda: {
                    "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}
                }
            ),
            parse=lambda: body,
        )

    client = SimpleNamespace(
        responses=SimpleNamespace(with_raw_response=SimpleNamespace(create=create))
    )
    budget = ControlledBudget(events, fail)
    result = openai_adapter.interpret(
        "Receita", [], date(2026, 8, 17), client=client, model="unit-model", budget=budget
    )
    return result, budget


def test_durable_dispatch_precedes_network_and_complete_usage_is_recorded() -> None:
    events = []
    answer, budget = invoke(events)
    assert answer.status == "needs_clarification"
    assert events == ["reserve", "dispatch-commit", "network", "record"]
    assert budget.records[0].total_tokens == 110


def test_missing_budget_capacity_never_touches_network() -> None:
    events = []
    with pytest.raises(BudgetRejected):
        invoke(events, fail="reserve")
    assert events == ["reserve"]


def test_failed_dispatch_never_touches_network_and_requests_only_predispatch_cancel() -> None:
    events = []
    with pytest.raises(BudgetRejected):
        invoke(events, fail="dispatch")
    assert events == ["reserve", "dispatch-commit", "cancel-before-dispatch"]


def test_evaluation_rejection_releases_only_application_predispatch_reservation() -> None:
    events = []
    rejected = Mock(side_effect=RuntimeError("evaluation budget exhausted"))
    recorded = Mock()
    with observe_provider(EvaluationHooks(reserve=rejected, record=recorded)):
        with pytest.raises(RuntimeError, match="evaluation budget"):
            invoke(events)
    assert events == ["reserve", "cancel-before-dispatch"]
    recorded.assert_not_called()


def test_timeout_after_dispatch_is_observed_without_cancel_or_retry() -> None:
    events = []
    error = APITimeoutError(request=httpx.Request("POST", "https://unit.invalid"))
    with pytest.raises(openai_adapter.ProviderUnavailable, match="Tempo limite"):
        invoke(events, network_error=error)
    assert events == ["reserve", "dispatch-commit", "network", "record"]


def test_failure_recording_usage_does_not_cancel_dispatched_reservation() -> None:
    events = []
    with pytest.raises(BudgetRejected, match="reservation remains"):
        invoke(events, fail="record")
    assert events == ["reserve", "dispatch-commit", "network", "record"]
