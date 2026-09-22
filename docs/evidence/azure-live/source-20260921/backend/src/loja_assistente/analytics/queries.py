from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo

from sqlalchemy import Date, Numeric, and_, cast, distinct, func, select, text
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import (
    CoverageResult,
    MissingDay,
    Period,
    ResultRow,
    Totals,
)
from loja_assistente.auth.service import Principal, assert_store_access
from loja_assistente.models import Coverage, Order, OrderItem, Product

BUSINESS_TIMEZONE = "America/Sao_Paulo"
LOCAL_ZONE = ZoneInfo(BUSINESS_TIMEZONE)


def money_ratio(revenue: int, orders: int) -> str | None:
    if orders == 0:
        return None
    with localcontext() as context:
        context.prec = max(28, len(str(abs(revenue))) + 12)
        return decimal_text(Decimal(revenue) / Decimal(orders))


def decimal_text(value: Decimal) -> str:
    raw = format(value, "f")
    whole, separator, fractional = raw.partition(".")
    return whole + "." + fractional.ljust(2, "0") if separator else raw + ".00"


def totals(revenue: int, orders: int, units: int) -> Totals:
    return Totals(
        revenue_cents=revenue,
        orders=orders,
        units=units,
        average_ticket_cents=money_ratio(revenue, orders),
    )


def metric_value(values: Totals, metric: str) -> Decimal | None:
    if metric == "average_ticket":
        ratio = money_ratio(values.revenue_cents, values.orders)
        return Decimal(ratio) if ratio is not None else None
    return Decimal(
        {"revenue": values.revenue_cents, "orders": values.orders, "units": values.units}[metric]
    )


def present_value(value: Decimal | None, metric: str) -> str | None:
    if value is None:
        return None
    if metric == "average_ticket":
        return decimal_text(value)
    return str(int(value))


@dataclass
class WindowResult:
    totals: Totals | None
    evidence: list[ResultRow]
    ranking: list[ResultRow]
    coverage: CoverageResult


def read_window(
    db: Session,
    principal: Principal,
    store_ids: list[str],
    period: Period,
    ranking_metric: str | None = None,
    limit: int = 5,
) -> WindowResult:
    # Revalidate permissions at the data boundary, even for an already resolved plan.
    assert_store_access(db, principal, store_ids)
    db.execute(text("SET LOCAL statement_timeout = '3000ms'"))
    covered_pairs = set(
        db.execute(
            select(Coverage.store_id, Coverage.date).where(
                Coverage.tenant_id == principal.tenant_id,
                Coverage.store_id.in_(store_ids),
                Coverage.date >= period.start,
                Coverage.date < period.end,
            )
        ).all()
    )
    days = [
        period.start + timedelta(days=offset) for offset in range((period.end - period.start).days)
    ]
    missing = [
        MissingDay(store_id=store_id, date=day)
        for day in days
        for store_id in store_ids
        if (store_id, day) not in covered_pairs
    ]
    expected = len(days) * len(store_ids)
    coverage = CoverageResult(
        status="absent" if not covered_pairs else "partial" if missing else "complete",
        covered_days=len(covered_pairs),
        expected_days=expected,
        missing=missing,
    )
    if not covered_pairs:
        return WindowResult(None, [], [], coverage)

    start_utc = datetime.combine(period.start, time.min, LOCAL_ZONE).astimezone(UTC)
    end_utc = datetime.combine(period.end, time.min, LOCAL_ZONE).astimezone(UTC)
    commercial_day = cast(func.timezone(BUSINESS_TIMEZONE, Order.occurred_at), Date)
    revenue = func.sum(
        cast(OrderItem.quantity, Numeric) * OrderItem.unit_price_cents - OrderItem.discount_cents
    )
    order_count = func.count(distinct(Order.id))
    unit_count = func.sum(OrderItem.quantity)
    base = (
        select(revenue.label("revenue"), order_count.label("orders"), unit_count.label("units"))
        .select_from(Order)
        .join(
            OrderItem, and_(OrderItem.tenant_id == Order.tenant_id, OrderItem.order_id == Order.id)
        )
        .join(
            Coverage,
            and_(
                Coverage.tenant_id == Order.tenant_id,
                Coverage.store_id == Order.store_id,
                Coverage.date == commercial_day,
            ),
        )
        .where(
            Order.tenant_id == principal.tenant_id,
            OrderItem.tenant_id == principal.tenant_id,
            Coverage.tenant_id == principal.tenant_id,
            Order.store_id.in_(store_ids),
            Coverage.store_id.in_(store_ids),
            Order.occurred_at >= start_utc,
            Order.occurred_at < end_utc,
            Order.status == "completed",
        )
    )
    daily = {
        row.day: totals(int(row.revenue), int(row.orders), int(row.units))
        for row in db.execute(
            base.add_columns(commercial_day.label("day")).group_by(commercial_day)
        )
    }
    covered_dates: set[date] = {pair[1] for pair in covered_pairs}
    evidence = [
        ResultRow(
            key=day.isoformat(),
            label=day.isoformat(),
            **daily.get(day, totals(0, 0, 0)).model_dump(),
        )
        for day in days
        if day in covered_dates
    ]
    total = totals(
        sum(row.revenue_cents for row in evidence),
        sum(row.orders for row in evidence),
        sum(row.units for row in evidence),
    )
    ranking: list[ResultRow] = []
    if ranking_metric is not None:
        order_metric = revenue if ranking_metric == "revenue" else unit_count
        ranking_query = (
            base.join(
                Product,
                and_(Product.tenant_id == OrderItem.tenant_id, Product.id == OrderItem.product_id),
            )
            .where(Product.tenant_id == principal.tenant_id)
            .add_columns(Product.id, Product.name)
            .group_by(Product.id, Product.name)
            .order_by(order_metric.desc(), Product.id.asc())
            .limit(limit)
        )
        ranking = [
            ResultRow(
                key=row.id,
                label=row.name,
                **totals(int(row.revenue), int(row.orders), int(row.units)).model_dump(),
            )
            for row in db.execute(ranking_query)
        ]
    return WindowResult(total, evidence, ranking, coverage)
