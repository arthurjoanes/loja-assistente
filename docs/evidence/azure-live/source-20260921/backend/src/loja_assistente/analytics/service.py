from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext

from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import (
    AnalyticsResult,
    Comparison,
    Period,
    QueryPlan,
    StoreScope,
)
from loja_assistente.analytics.queries import (
    BUSINESS_TIMEZONE,
    metric_value,
    present_value,
    read_window,
)
from loja_assistente.auth.service import Principal, resolve_store_references
from loja_assistente.config import settings
from loja_assistente.models import Dataset

FORMULAS = {
    "revenue": "Soma de quantidade × preço unitário − desconto total do item, nos pedidos concluídos.",
    "orders": "Contagem de pedidos concluídos distintos nas lojas e no período consultados.",
    "average_ticket": "Receita líquida ÷ pedidos concluídos; arredondamento HALF_UP na apresentação.",
    "units": "Soma das quantidades dos itens de pedidos concluídos.",
}


def execute_query(
    db: Session, principal: Principal, plan: QueryPlan, request_id: str
) -> AnalyticsResult:
    stores = resolve_store_references(db, principal, plan.store_references)
    ids = [store.id for store in stores]
    window = read_window(
        db,
        principal,
        ids,
        plan.period,
        plan.metric if plan.intent == "ranking" else None,
        plan.limit,
    )
    current = metric_value(window.totals, plan.metric) if window.totals is not None else None
    comparison = None
    if plan.comparison is not None:
        length = (plan.period.end - plan.period.start).days
        previous_period = Period(
            start=plan.period.start - timedelta(days=length), end=plan.period.start
        )
        previous = read_window(db, principal, ids, previous_period)
        value = None
        change = None
        if window.coverage.status != "complete" or previous.coverage.status != "complete":
            message = "Comparação indisponível: faltam dados em um dos períodos."
        else:
            previous_value = (
                metric_value(previous.totals, plan.metric) if previous.totals is not None else None
            )
            value = present_value(previous_value, plan.metric)
            if previous_value is None or current is None:
                message = "Comparação indisponível: um dos períodos não tem pedidos."
            elif previous_value == 0:
                message = "Variação percentual indisponível: período anterior com valor zero."
            else:
                with localcontext() as context:
                    context.prec = max(28, len(str(current)) + len(str(previous_value)) + 12)
                    change = format(
                        ((current - previous_value) / previous_value * 100).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        ),
                        "f",
                    )
                message = "Período anterior de mesma duração, nas mesmas lojas."
        comparison = Comparison(
            period=previous_period, value=value, change_percent=change, message=message
        )
    version = db.scalar(select(Dataset.version).limit(1)) or settings.dataset_version
    return AnalyticsResult(
        intent=plan.intent,
        metric=plan.metric,
        scope=[StoreScope(id=store.id, name=store.name) for store in stores],
        period=plan.period,
        timezone=BUSINESS_TIMEZONE,
        currency="BRL",
        unit="centavos"
        if plan.metric in ("revenue", "average_ticket")
        else "pedidos"
        if plan.metric == "orders"
        else "unidades",
        formula=FORMULAS[plan.metric],
        value=present_value(current, plan.metric),
        totals=window.totals,
        rows=window.ranking
        if plan.intent == "ranking"
        else window.evidence
        if plan.intent == "daily"
        else [],
        coverage=window.coverage,
        comparison=comparison,
        evidence=window.evidence,
        dataset_version=version,
        request_id=request_id,
    )
