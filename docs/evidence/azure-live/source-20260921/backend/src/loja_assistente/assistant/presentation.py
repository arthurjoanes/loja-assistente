from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext

from loja_assistente.analytics.contracts import AnalyticsResult

LABELS = {
    "revenue": "Receita líquida",
    "orders": "Pedidos concluídos",
    "average_ticket": "Ticket médio",
    "units": "Unidades vendidas",
}


def format_value(value: str | None, metric: str) -> str:
    if value is None:
        return "indisponível"
    if metric in ("revenue", "average_ticket"):
        with localcontext() as context:
            context.prec = max(28, len(value) + 4)
            amount = (Decimal(value) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return "R$ " + f"{amount:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
    return value


def describe(result: AnalyticsResult) -> str:
    if result.coverage.status == "absent":
        return "Sem dados para as lojas e o período selecionados. Escolha outro período."
    end = result.period.end - timedelta(days=1)
    message = f"{LABELS[result.metric]}: {format_value(result.value, result.metric)} de {result.period.start:%d/%m/%Y} a {end:%d/%m/%Y}."
    if result.intent == "ranking":
        message += f" Ranking de {len(result.rows)} produtos por {'receita' if result.metric == 'revenue' else 'unidades'}. O total inclui todos os produtos."
    if result.coverage.status == "partial":
        message += " Cobertura parcial: total calculado apenas nos dias carregados."
    if result.comparison:
        if result.comparison.change_percent is not None:
            message += f" Variação de {result.comparison.change_percent.replace('.', ',')}% sobre o período anterior."
        else:
            message += " " + result.comparison.message
    return message
