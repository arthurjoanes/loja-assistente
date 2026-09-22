"Interpreta perguntas demo em ordem fixa."

from datetime import date

from pydantic import ValidationError

from loja_assistente.analytics.contracts import Period, QueryPlan, StoreScope
from loja_assistente.assistant.contracts import Interpretation
from loja_assistente.assistant.filter_limits import (
    unsupported_filter,
    without_conversational_prefix,
)
from loja_assistente.assistant.interpreters.demo_language import (
    parse_capability,
    supported_vocabulary,
)
from loja_assistente.assistant.interpreters.demo_periods import continuation_plan, select_period
from loja_assistente.assistant.interpreters.store_mentions import resolve_mentions

VERSION = "demo-patterns-v4"
HELP = "Informe um indicador e um período. Ex.: receita de ontem."


def clarify(message: str = HELP) -> Interpretation:
    return Interpretation(status="needs_clarification", plan=None, message=message)


def interpret(
    question: str,
    stores: list[StoreScope],
    reference_date: date,
    previous_plan: QueryPlan | None = None,
    period: Period | None = None,
    store_ids: list[str] | None = None,
) -> Interpretation:
    text = without_conversational_prefix(question)
    if not text:
        return clarify(
            "Olá! Posso consultar receita, pedidos, ticket, unidades e ranking. Qual indicador e período deseja consultar?"
        )
    filter_problem = unsupported_filter(question)
    if filter_problem:
        return clarify(filter_problem)
    if any(
        word in text
        for word in ("cancelad", "bruto", "sem desconto", "por mes", "por semana", "por loja")
    ):
        return clarify(
            "Use agrupamento diário ou por produto. As métricas consideram pedidos concluídos, com descontos."
        )
    blocked = ("ignore", "administrador", "sql", "select ", "drop ", "system prompt")
    unsupported = (
        "lucro",
        "margem",
        "estoque",
        "previs",
        "amanha",
        "repor",
        "comprar",
        "recomend",
        "por que",
        "porque",
        "causa",
        "cliente",
        "cpf",
        "tribut",
        "reembolso",
    )
    if any(word in text for word in blocked):
        return Interpretation(
            status="unsupported",
            plan=None,
            message="Consulte os indicadores disponíveis nas suas lojas.",
        )
    if any(word in text for word in unsupported):
        return Interpretation(
            status="unsupported",
            plan=None,
            message="Indicador não disponível. Use receita, pedidos, ticket, unidades ou ranking de produtos.",
        )

    try:
        prior = continuation_plan(text, previous_plan)
        if prior is not None:
            return Interpretation(status="ready", plan=prior, message="")
        if not supported_vocabulary(text, stores):
            return clarify("Termos ou filtros não reconhecidos. Ex.: receita da loja Centro ontem.")
        capability = parse_capability(text)
        effective_period, comparison = select_period(text, reference_date, period)
        references = resolve_mentions(text, stores)
        if references is None:
            return clarify("Nome de loja ambíguo. Use o ID da loja.")
        plan = QueryPlan(
            intent=capability.intent,
            metric=capability.metric,
            store_references=references or store_ids or [store.id for store in stores],
            period=effective_period,
            comparison=comparison,
            grouping="day" if capability.intent == "daily" else None,
            limit=capability.limit,
        )
    except (ValueError, OverflowError) as error:
        # Domain errors explain the choice; schema errors may include internal input values.
        if isinstance(error, ValidationError):
            return clarify("Use datas válidas, de 1 a 90 dias e ranking com 1 a 20 produtos.")
        if isinstance(error, OverflowError):
            return clarify("Use datas válidas em um intervalo de 1 a 90 dias.")
        return clarify(str(error) or "Use datas válidas em um intervalo de 1 a 90 dias.")
    return Interpretation(status="ready", plan=plan, message="")
