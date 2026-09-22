"""Durable PostgreSQL/API proof. Never replaces these checks with SQLite or mocks of locks.

Client transport is fake; reservations, committed transactions and API authorization
are real. Existing savepoint fixtures are not used for independent ledger sessions.
"""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from pathlib import Path
from threading import Lock
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from manual_fixture import ORIGIN, PASSWORD, fixture_password_hash
from openai import OpenAI
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker
from test_interpreters import response_body

from loja_assistente.app import app
from loja_assistente.assistant import budget as budget_module
from loja_assistente.assistant import interpretation
from loja_assistente.assistant.budget import DurableBudget
from loja_assistente.assistant.budget_policy import BudgetRejected
from loja_assistente.assistant.provider_trace import (
    EvaluationHooks,
    ProviderTrace,
    observe_provider,
)
from loja_assistente.config import settings
from loja_assistente.database import Base, get_db
from loja_assistente.models import (
    AnswerRecord,
    Conversation,
    Organization,
    ProviderBudgetAccount,
    ProviderReservation,
    Store,
    StorePermission,
    User,
)


class FakeProvider:
    def __init__(self):
        self.calls = 0
        self.lock = Lock()
        self.timeout = False
        self.input_tokens = 100
        self.output_tokens = 10
        self.inspect_dispatch = None

    def transport(self, request):
        with self.lock:
            self.calls += 1
            call = self.calls
        if self.inspect_dispatch:
            self.inspect_dispatch()
        if self.timeout:
            raise httpx.ReadTimeout("controlled response loss", request=request)
        payload = response_body(
            {
                "type": "output_text",
                "annotations": [],
                "text": json.dumps(
                    {"status": "needs_clarification", "plan": None, "message": "Qual período?"}
                ),
            }
        )
        payload["id"] = f"response-budget-{call}"
        payload["usage"] = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
        }
        return httpx.Response(
            200, json=payload, headers={"x-request-id": f"provider-budget-{call}"}
        )


@pytest.fixture
def durable_api(test_engine, monkeypatch, request):
    identity = "budget-" + uuid4().hex
    tenants = [identity, identity + "-other"]
    sessions = sessionmaker(bind=test_engine, expire_on_commit=False)
    with sessions.begin() as setup:
        setup.add_all([Organization(id=name, name="Synthetic budget fixture") for name in tenants])
        setup.flush()
        setup.add(
            User(
                id=identity,
                tenant_id=identity,
                name="Budget operator",
                email=identity + "@example.invalid",
                role="manager",
                password_hash=fixture_password_hash(),
            )
        )
        setup.add(
            Store(
                id="budget-store",
                tenant_id=identity,
                external_id="budget-store",
                name="Budget fixture store",
            )
        )
        setup.flush()
        setup.add(StorePermission(tenant_id=identity, user_id=identity, store_id="budget-store"))
    ledger = DurableBudget(identity, identity, "component-test", sessions)
    ledger.configure(2, 200000, 2000, "Synthetic PostgreSQL proof; no paid transport")
    other = DurableBudget(tenants[1], identity, "component-test", sessions)
    other.configure(2, 200000, 2000, "Synthetic independent organization")
    fake = FakeProvider()
    monkeypatch.setattr(budget_module, "SessionLocal", sessions)
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "controlled-fake-transport-only")
    monkeypatch.setattr(settings, "reference_date", date(2026, 8, 17))
    monkeypatch.setattr(
        interpretation,
        "OpenAI",
        lambda **kwargs: OpenAI(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(fake.transport))
        ),
    )

    def dependency():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = dependency
    try:
        with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
            login = client.post(
                "/api/auth/login",
                json={"email": identity + "@example.invalid", "password": PASSWORD},
            )
            assert login.status_code == 200, login.text
            client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            yield {
                "client": client,
                "ledger": ledger,
                "other": other,
                "fake": fake,
                "sessions": sessions,
                "tenant": identity,
                "engine": test_engine,
            }
    finally:
        app.dependency_overrides.clear()
        output = os.environ.get("BUDGET_PROOF_OUTPUT_DIR")
        if output:
            try:
                account = ledger.summary()
            except BudgetRejected:
                account = {"tenant_id": identity, "account_absent": True}
            directory = Path(output)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / (request.node.name + ".json")).write_text(
                json.dumps(
                    {
                        "test": request.node.nodeid,
                        "transport": "httpx.MockTransport; no paid provider",
                        "provider_calls": fake.calls,
                        "final_observation_before_fixture_cleanup": account,
                        "pass_fail_authority": "JUnit test result, not this observation",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        with sessions.begin() as cleanup:
            # Exact newly generated tenant IDs only; no global truncation or shared fixture reset.
            for table in reversed(Base.metadata.sorted_tables):
                if "tenant_id" in table.c:
                    cleanup.execute(delete(table).where(table.c.tenant_id.in_(tenants)))
            cleanup.execute(delete(Organization).where(Organization.id.in_(tenants)))


def ask(fixture):
    return fixture["client"].post(
        "/api/assistant/query", json={"question": "Qual foi a receita ontem?", "mode": "llm"}
    )


def trace(call="component-call", **changes):
    base = ProviderTrace(
        call_id=call,
        model_requested="controlled-model",
        prompt_sha256="a" * 64,
        schema_sha256="b" * 64,
    )
    return replace(base, **changes)


def test_eight_real_api_sessions_can_dispatch_only_two_calls(durable_api):
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: ask(durable_api), range(8)))
    assert all(response.status_code == 200 for response in responses)
    assert (
        sorted(response.json()["status"] for response in responses)
        == ["needs_clarification"] * 2 + ["provider_error"] * 6
    )
    summary = durable_api["ledger"].summary()
    assert durable_api["fake"].calls == 2
    assert summary["committed"] == {"calls": 2, "input_units": 200, "output_units": 20}
    assert len(summary["reservations"]) == 2
    assert {row["state"] for row in summary["reservations"]} == {"reconciled"}


def test_provider_is_called_after_dispatch_commit_without_account_lock(durable_api):
    observed = []

    def inspect_dispatch():
        with durable_api["sessions"].begin() as connection:
            account = connection.scalar(
                select(ProviderBudgetAccount)
                .where(ProviderBudgetAccount.tenant_id == durable_api["tenant"])
                .with_for_update(nowait=True)
            )
            rows = connection.scalars(
                select(ProviderReservation).where(
                    ProviderReservation.tenant_id == durable_api["tenant"]
                )
            ).all()
            observed.append((account.committed_calls, [row.state for row in rows]))

    durable_api["fake"].inspect_dispatch = inspect_dispatch
    assert ask(durable_api).json()["status"] == "needs_clarification"
    assert observed == [(1, ["dispatched"])]


def test_predispatch_cancel_is_idempotent_and_terminal(durable_api):
    ledger = durable_api["ledger"]
    call = trace()
    ledger.reserve(call, 1000, 100)
    ledger.cancel_before_dispatch(call.call_id)
    before = ledger.summary()
    ledger.cancel_before_dispatch(call.call_id)
    assert ledger.summary() == before
    assert before["committed"] == {"calls": 0, "input_units": 0, "output_units": 0}
    for action in (
        lambda: ledger.reserve(call, 1000, 100),
        lambda: ledger.dispatch(call.call_id),
        lambda: ledger.record(call),
    ):
        with pytest.raises(BudgetRejected):
            action()
    assert ledger.summary() == before


def test_timeout_survives_a_new_process_and_prevents_third_dispatch(durable_api):
    durable_api["fake"].timeout = True
    for _ in range(3):
        assert ask(durable_api).json()["status"] == "provider_error"
    summary = durable_api["ledger"].summary()
    assert durable_api["fake"].calls == 2 and summary["committed"]["calls"] == 2
    assert {row["state"] for row in summary["reservations"]} == {"unknown"}
    assert summary["committed"]["input_units"] == sum(
        row["reserved_input"] for row in summary["reservations"]
    )
    program = (
        "import json; from loja_assistente.assistant.budget import DurableBudget; print(json.dumps(DurableBudget("
        + repr(durable_api["tenant"])
        + ",'probe','probe').summary(),sort_keys=True))"
    )
    child = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=20,
        env={
            **os.environ,
            "DATABASE_URL": durable_api["engine"].url.render_as_string(hide_password=False),
            "OPENAI_API_KEY": "",
            "LLM_ENABLED": "false",
        },
    )
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == summary


def test_predispatch_evaluation_refusal_cancels_once_without_network(durable_api):
    def deny(*_args):
        raise BudgetRejected("Synthetic evaluation refusal")

    with observe_provider(EvaluationHooks(reserve=deny, record=lambda _: None)):
        assert ask(durable_api).json()["status"] == "provider_error"
    summary = durable_api["ledger"].summary()
    assert durable_api["fake"].calls == 0
    assert summary["committed"] == {"calls": 0, "input_units": 0, "output_units": 0}
    assert [row["state"] for row in summary["reservations"]] == ["canceled"]


def test_response_transaction_rollback_does_not_refund_dispatched_unknown(durable_api, monkeypatch):
    from loja_assistente.assistant import service

    original = service.record_operation
    durable_api["fake"].timeout = True

    def fail(*_args, **_kwargs):
        raise RuntimeError("Synthetic response write failure")

    monkeypatch.setattr(service, "record_operation", fail)
    response = ask(durable_api)
    # The application middleware intentionally sanitizes errors into an HTTP response.
    assert response.status_code == 500
    assert response.json()["detail"] == "Falha na consulta. Tente novamente."
    summary = durable_api["ledger"].summary()
    assert summary["committed"]["calls"] == 1
    assert summary["reservations"][0]["state"] == "unknown"
    assert durable_api["fake"].calls == 1
    with durable_api["sessions"]() as check:
        for model in (AnswerRecord, Conversation):
            assert (
                check.scalar(select(model.id).where(model.tenant_id == durable_api["tenant"]))
                is None
            )
    monkeypatch.setattr(service, "record_operation", original)


def test_known_reconciliation_is_idempotent_and_conflicting_usage_refused(durable_api):
    ledger = durable_api["ledger"]
    call = trace()
    ledger.reserve(call, 1000, 100)
    ledger.dispatch(call.call_id)
    observed = replace(
        call,
        input_tokens=100,
        output_tokens=10,
        total_tokens=110,
        provider_request_id="fake-evidence",
    )
    ledger.record(observed)
    first = ledger.summary()
    ledger.record(observed)
    assert ledger.summary() == first
    with pytest.raises(BudgetRejected, match="incompatível"):
        ledger.record(replace(observed, input_tokens=101, total_tokens=111))
    assert ledger.summary() == first
    with pytest.raises(BudgetRejected):
        ledger.cancel_before_dispatch(call.call_id)
    with pytest.raises(BudgetRejected):
        ledger.dispatch(call.call_id)


def test_adapter_reconciliation_rejects_another_user_or_request_in_same_tenant(durable_api):
    ledger = durable_api["ledger"]
    call = trace()
    ledger.reserve(call, 1000, 100)
    ledger.dispatch(call.call_id)
    observed = replace(call, input_tokens=100, output_tokens=10, total_tokens=110)
    before = ledger.summary()
    for user, request in (
        ("different-user", ledger.request_id),
        (ledger.user_id, "different-request"),
    ):
        wrong = DurableBudget(ledger.tenant_id, user, request, durable_api["sessions"])
        with pytest.raises(BudgetRejected, match="outra solicitação"):
            wrong.record(observed)
    assert ledger.summary() == before


def test_accounts_cannot_access_each_others_call_ids(durable_api):
    ledger, other = durable_api["ledger"], durable_api["other"]
    call = trace()
    ledger.reserve(call, 1000, 100)
    for method in (other.dispatch, other.cancel_before_dispatch):
        with pytest.raises(BudgetRejected, match="nesta organização"):
            method(call.call_id)
    with pytest.raises(BudgetRejected, match="nesta organização"):
        other.record(call)
    assert other.summary()["committed"]["calls"] == 0
    other.reserve(call, 1000, 100)
    assert ledger.summary()["committed"]["calls"] == other.summary()["committed"]["calls"] == 1


def test_observed_overrun_blocks_next_api_call_without_erasing_actual_usage(durable_api):
    durable_api["fake"].input_tokens = 250000
    assert ask(durable_api).json()["status"] == "needs_clarification"
    summary = durable_api["ledger"].summary()
    assert summary["blocked"] and summary["committed"]["input_units"] == 250000
    assert summary["committed"]["input_units"] > summary["limits"]["input_units"]
    assert ask(durable_api).json()["status"] == "provider_error"
    assert durable_api["fake"].calls == 1
    durable_api["ledger"].configure(
        10, 500000, 10000, "Explicit higher ceiling does not forgive an overrun"
    )
    assert durable_api["ledger"].summary()["blocked"]


def test_unknown_requires_complete_identified_evidence_and_cannot_be_canceled(durable_api):
    ledger = durable_api["ledger"]
    call = trace()
    ledger.reserve(call, 1000, 100)
    ledger.dispatch(call.call_id)
    ledger.record(replace(call, status="timeout"))
    before = ledger.summary()
    with pytest.raises(BudgetRejected):
        ledger.cancel_before_dispatch(call.call_id)
    with pytest.raises(BudgetRejected):
        ledger.reconcile(call, source="operator_evidence", evidence_reference="Missing usage")
    assert ledger.summary() == before
    observed = replace(
        call,
        input_tokens=100,
        output_tokens=10,
        total_tokens=110,
        provider_request_id="fake-result-ledger-1",
    )
    for invalid_id in ("", "   ", "x" * 201):
        with pytest.raises(BudgetRejected, match="ID do provedor"):
            ledger.reconcile(
                replace(observed, provider_request_id=invalid_id),
                source="operator_evidence",
                evidence_reference="Synthetic controlled invalid provider ID",
            )
        assert ledger.summary() == before
    with pytest.raises(BudgetRejected, match="referência"):
        ledger.reconcile(observed, source="operator_evidence", evidence_reference="   ")
    assert ledger.summary() == before
    ledger.reconcile(
        observed,
        source="operator_evidence",
        evidence_reference="Synthetic fake-provider evidence, not a paid invoice",
    )
    final = ledger.summary()
    assert final["committed"] == {"calls": 1, "input_units": 100, "output_units": 10}
    ledger.reconcile(
        observed, source="operator_evidence", evidence_reference="Same synthetic evidence"
    )
    assert ledger.summary() == final


def test_missing_account_fails_closed_and_unsupported_filter_needs_no_reservation(durable_api):
    ledger = durable_api["ledger"]
    with durable_api["sessions"].begin() as session:
        session.execute(
            delete(ProviderBudgetAccount).where(ProviderBudgetAccount.tenant_id == ledger.tenant_id)
        )
    response = ask(durable_api)
    assert response.json()["status"] == "provider_error" and durable_api["fake"].calls == 0
    response = durable_api["client"].post(
        "/api/assistant/query",
        json={"question": "Receita ontem somente por categoria calçados", "mode": "llm"},
    )
    assert response.json()["status"] in ("needs_clarification", "unsupported")
    assert durable_api["fake"].calls == 0
    with durable_api["sessions"]() as session:
        assert (
            session.scalar(
                select(ProviderReservation.call_id).where(
                    ProviderReservation.tenant_id == ledger.tenant_id
                )
            )
            is None
        )
