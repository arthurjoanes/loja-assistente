"""Keep the API ledger committed while evaluation answers remain rollback-isolated.

Only the two synthetic organizations/accounts are committed. A different approval
cannot silently replace a previous ledger. The external evaluation journal remains
an additional global cap shared across organizations and stages.
"""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from evals.live_budget import BudgetStopped, LiveBudget
from loja_assistente.assistant.budget import DurableBudget
from loja_assistente.models import Organization, ProviderBudgetAccount

ORGANIZATIONS = {"org_a": "Aurora Comércio", "org_b": "Brisa Comércio"}


def prepare_api_budget(engine: Engine, budget: LiveBudget) -> dict:
    if (
        not (engine.url.database or "").endswith("_test")
        or engine.url.get_backend_name() != "postgresql"
    ):
        raise BudgetStopped(
            "O ledger de avaliação exige PostgreSQL descartável terminado em _test."
        )
    reason = "Evaluation authorization sha256:" + budget.contract_hash
    # Inspect before creating anything, so a pre-existing foreign account is rejected.
    with Session(engine) as check:
        for tenant, name in ORGANIZATIONS.items():
            organization = check.get(Organization, tenant)
            account = check.get(ProviderBudgetAccount, tenant)
            if organization and (organization.name != name or account is None):
                raise BudgetStopped(
                    "Banco já contém organizações fora deste contrato; use banco exclusivo novo."
                )
            if account and account.configured_reason != reason:
                raise BudgetStopped(
                    "Outra autorização já possui o ledger; não zerar uso. Use banco exclusivo novo."
                )
    with Session(engine) as setup, setup.begin():
        for tenant, name in ORGANIZATIONS.items():
            if setup.get(Organization, tenant) is None:
                setup.add(Organization(id=tenant, name=name))
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    for tenant in ORGANIZATIONS:
        DurableBudget(tenant, "evaluation-setup", "evaluation-setup", sessions).configure(
            budget.contract["max_calls"],
            budget.contract["max_input_tokens"],
            budget.contract["max_output_tokens"],
            reason,
        )
    return {
        "authorization_sha256": budget.contract_hash,
        "tenants": sorted(ORGANIZATIONS),
        "organizations_and_accounts_committed": True,
        "answers_rolled_back": True,
        "ledger_retained": True,
        "automatic_reset": False,
        "scope": "Application limits per tenant plus existing external journal global limits; no extra live calls authorized.",
    }
