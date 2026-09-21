from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import Period, QueryPlan
from loja_assistente.analytics.queries import money_ratio
from loja_assistente.analytics.service import execute_query
from loja_assistente.auth.service import Principal
from loja_assistente.models import Coverage

MANAGER = Principal("manager_a", "org_a", "Marina", "gerente.a@demo.local", "manager")
OTHER = Principal("manager_b", "org_b", "Bruno", "gerente.b@demo.local", "manager")


def test_ticket_keeps_precision_until_final_currency_presentation() -> None:
    assert money_ratio(20099, 200) == "100.495"
    assert money_ratio(100, 3) == "33.33333333333333333333333333"


def plan(start: str = "2026-08-16", end: str = "2026-08-17", **kwargs: object) -> QueryPlan:
    return QueryPlan.model_validate(
        {
            "intent": "aggregate",
            "metric": "revenue",
            "store_references": [],
            "period": {"start": start, "end": end},
            **kwargs,
        }
    )


def test_independent_financial_oracle_with_multi_item_orders(db: Session) -> None:
    result = execute_query(db, MANAGER, plan(), "oracle")
    assert result.value == "3000"
    assert result.totals is not None
    assert result.totals.model_dump() == {
        "revenue_cents": 3000,
        "orders": 2,
        "units": 8,
        "average_ticket_cents": "1500.00",
    }
    assert result.scope[0].id == "a001"
    assert result.coverage.status == "complete"
    assert result.dataset_version == "manual-v1"


def test_same_external_identifiers_do_not_join_tenants(db: Session) -> None:
    own = execute_query(db, MANAGER, plan(), "first")
    other = execute_query(db, OTHER, plan(), "second")
    assert own.value == "3000"
    assert other.value == "3300"
    assert [store.id for store in other.scope] == ["b001"]


def test_utc_midnight_boundary_and_exclusive_end(db: Session) -> None:
    before = execute_query(db, MANAGER, plan("2026-08-14", "2026-08-15"), "before")
    after = execute_query(db, MANAGER, plan("2026-08-15", "2026-08-16"), "after")
    assert before.value == "2500"  # 02:59:59 UTC still belongs to the previous business day.
    assert after.value == "1600"  # 03:00:00 UTC starts the next business day.


def test_ranking_tie_is_deterministic_and_counts_product_orders(db: Session) -> None:
    result = execute_query(db, MANAGER, plan(intent="ranking", limit=3), "ranking")
    assert [(row.key, row.revenue_cents, row.orders) for row in result.rows] == [
        ("pa01", 1000, 1),
        ("pa02", 1000, 1),
        ("pa03", 1000, 1),
    ]
    units = execute_query(db, MANAGER, plan(intent="ranking", metric="units", limit=2), "units")
    assert [(row.key, row.units) for row in units.rows] == [("pa03", 5), ("pa02", 2)]


def test_daily_zero_is_only_emitted_for_covered_day(db: Session) -> None:
    result = execute_query(
        db, MANAGER, plan("2026-08-13", "2026-08-17", intent="daily", grouping="day"), "daily"
    )
    assert [row.revenue_cents for row in result.rows] == [0, 2500, 1600, 3000]
    assert result.rows == result.evidence
    assert result.totals is not None and result.totals.orders == 4
    assert result.totals.average_ticket_cents == "1775.00"


def test_absence_is_not_financial_zero(db: Session) -> None:
    result = execute_query(db, MANAGER, plan("2026-08-18", "2026-08-19"), "absent")
    assert result.coverage.status == "absent"
    assert result.value is None and result.totals is None
    assert result.evidence == [] and result.rows == []


def test_partial_coverage_excludes_unloaded_sales_and_comparison(db: Session) -> None:
    db.execute(
        delete(Coverage).where(
            Coverage.tenant_id == "org_a",
            Coverage.store_id == "a001",
            Coverage.date == date(2026, 8, 16),
        )
    )
    result = execute_query(
        db, MANAGER, plan("2026-08-15", "2026-08-17", comparison="previous_period"), "partial"
    )
    assert result.value == "1600"
    assert result.coverage.status == "partial"
    assert result.coverage.covered_days == 1 and result.coverage.expected_days == 2
    assert result.comparison is not None and result.comparison.change_percent is None
    assert result.comparison.value is None
    assert [row.key for row in result.evidence] == ["2026-08-15"]


def test_equivalent_previous_period_percentage_and_zero_base(db: Session) -> None:
    result = execute_query(db, MANAGER, plan(comparison="previous_period"), "comparison")
    assert result.comparison is not None
    assert result.comparison.value == "1600" and result.comparison.change_percent == "87.50"
    assert result.comparison.period == Period(start=date(2026, 8, 15), end=date(2026, 8, 16))
    zero = execute_query(
        db, MANAGER, plan("2026-08-14", "2026-08-15", comparison="previous_period"), "zero"
    )
    assert zero.comparison is not None
    assert zero.comparison.value == "0" and zero.comparison.change_percent is None
    assert "zero" in zero.comparison.message


def test_zero_orders_has_no_average_ticket(db: Session) -> None:
    result = execute_query(
        db, MANAGER, plan("2026-08-12", "2026-08-13", metric="average_ticket"), "zero-ticket"
    )
    assert result.coverage.status == "complete" and result.value is None
    assert result.totals is not None and result.totals.average_ticket_cents is None
    assert result.totals.revenue_cents == 0


@pytest.mark.parametrize(
    "invalid",
    [
        {"sql": "select * from orders"},
        {"tenant_id": "org_b"},
        {"user_id": "manager_b"},
        {"limit": 21},
        {"limit": True},
        {"intent": "ranking", "metric": "average_ticket"},
        {"period": {"start": "2026-01-01", "end": "2026-08-17"}},
        {"period": {"start": "2026-08-17", "end": "2026-08-17"}},
    ],
)
def test_strict_query_contract(invalid: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        plan(**invalid)
