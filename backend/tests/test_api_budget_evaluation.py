from types import SimpleNamespace
from uuid import uuid4

import pytest
from evals import api_budget
from evals.live_budget import BudgetStopped
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from loja_assistente.assistant.budget import DurableBudget
from loja_assistente.assistant.provider_trace import ProviderTrace
from loja_assistente.models import Organization, ProviderBudgetAccount, ProviderReservation, User


@pytest.mark.parametrize(
    "url", ["postgresql+psycopg://test@invalid/production", "sqlite:///temporary_test"]
)
def test_evaluation_account_guard_rejects_before_connecting(url):
    engine = SimpleNamespace(url=make_url(url))
    with pytest.raises(BudgetStopped, match="PostgreSQL descartável"):
        api_budget.prepare_api_budget(engine, SimpleNamespace())


def test_evaluation_keeps_ledger_when_fixture_rolls_back_and_rejects_new_approval(
    test_engine, monkeypatch
):
    tenant = "eval-budget-" + uuid4().hex
    monkeypatch.setattr(api_budget, "ORGANIZATIONS", {tenant: "Synthetic committed ledger"})
    authorization = SimpleNamespace(
        contract_hash="a" * 64,
        contract={"max_calls": 2, "max_input_tokens": 20000, "max_output_tokens": 2000},
    )
    sessions = sessionmaker(bind=test_engine, expire_on_commit=False)
    try:
        metadata = api_budget.prepare_api_budget(test_engine, authorization)
        assert metadata["ledger_retained"] and not metadata["automatic_reset"]
        with test_engine.connect() as connection:
            outer = connection.begin()
            fixture = Session(bind=connection, join_transaction_mode="create_savepoint")
            try:
                fixture.add(
                    User(
                        id=tenant,
                        tenant_id=tenant,
                        name="Temporary evaluator",
                        email=tenant + "@example.invalid",
                        role="manager",
                        password_hash="not-used",
                    )
                )
                fixture.flush()
                ledger = DurableBudget(tenant, tenant, "evaluation-call", sessions)
                call = ProviderTrace(
                    call_id="fake-call",
                    model_requested="fake-model",
                    prompt_sha256="a" * 64,
                    schema_sha256="b" * 64,
                )
                ledger.reserve(call, 10000, 1000)
                ledger.dispatch(call.call_id)
                ledger.record(call)
            finally:
                fixture.close()
                outer.rollback()
        before = ledger.summary()
        assert before["reservations"][0]["state"] == "unknown"
        with sessions() as check:
            assert check.scalar(select(User.id).where(User.id == tenant)) is None
        api_budget.prepare_api_budget(test_engine, authorization)
        assert ledger.summary() == before
        other = SimpleNamespace(contract_hash="b" * 64, contract=authorization.contract)
        with pytest.raises(BudgetStopped, match="Outra autorização"):
            api_budget.prepare_api_budget(test_engine, other)
        assert ledger.summary() == before
    finally:
        with sessions.begin() as cleanup:
            cleanup.execute(
                delete(ProviderReservation).where(ProviderReservation.tenant_id == tenant)
            )
            cleanup.execute(
                delete(ProviderBudgetAccount).where(ProviderBudgetAccount.tenant_id == tenant)
            )
            cleanup.execute(delete(User).where(User.tenant_id == tenant))
            cleanup.execute(delete(Organization).where(Organization.id == tenant))
