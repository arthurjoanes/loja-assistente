"Vocabulário e precedência de métricas do modo demo."

import re
from dataclasses import dataclass
from typing import Literal

from loja_assistente.analytics.contracts import StoreScope
from loja_assistente.assistant.filter_limits import normalize
from loja_assistente.assistant.interpreters.store_mentions import explicit_store_names


@dataclass(frozen=True)
class Capability:
    intent: Literal["aggregate", "ranking", "daily"]
    metric: Literal["revenue", "orders", "average_ticket", "units"]
    limit: int = 5


def parse_capability(text: str) -> Capability:
    ranking = bool(
        re.search(r"\b(?:ranking|top|produtos mais|mais vendidos|produtos com maior)\b", text)
    )
    daily = bool(re.search(r"\b(?:evolucao|diari[ao]s?|por dia|dia a dia)\b", text))
    if ranking and daily:
        raise ValueError("Escolha ranking de produtos ou evolução diária em cada pergunta.")

    # Detect every explicit metric first; an ordered elif silently loses a second metric.
    metrics: set[Literal["revenue", "orders", "average_ticket", "units"]] = set()
    if re.search(
        r"\b(?:receita|faturamento|quanto (?:eu )?vend\w*|quanto entrou|valor vendido)\b", text
    ):
        metrics.add("revenue")
    if re.search(r"\b(?:pedidos?|quantas vendas)\b", text):
        metrics.add("orders")
    if re.search(r"\b(?:ticket|tiquete)\b", text):
        metrics.add("average_ticket")
    if re.search(r"\bunidades?\b", text) or ("quantidade" in text and "orders" not in metrics):
        metrics.add("units")
    if not metrics and "mais vendidos" in text:
        metrics.add("units")
    if len(metrics) > 1:
        raise ValueError("Escolha um indicador: receita, pedidos, ticket ou unidades.")
    if not metrics:
        raise ValueError("Qual indicador: receita, pedidos, ticket médio ou unidades?")
    metric = metrics.pop()
    if ranking and metric not in ("revenue", "units"):
        raise ValueError("Ranking por receita ou unidades?")
    if "produto" in text and not ranking:
        raise ValueError("Use ranking por receita ou unidades. Filtro por produto não disponível.")
    limits = re.findall(r"(?:top|ranking(?: de)?)\s+(\d+)|\b(\d+)\s+produtos", text)
    values = [int(first or second) for first, second in limits]
    if len(values) > 1:
        raise ValueError("Informe um limite de 1 a 20 produtos.")
    if values and not ranking:
        raise ValueError("Limite de produtos só se aplica a um ranking.")
    return Capability(
        "ranking" if ranking else "daily" if daily else "aggregate",
        metric,
        values[0] if values else 5,
    )


def supported_vocabulary(text: str, stores: list[StoreScope]) -> bool:
    # A bounded demo must not silently discard a product name or an unknown qualifier.
    # Explicit store names are resolved separately and remain subject to authorization.
    remaining = text
    names = [store.name for store in stores] + explicit_store_names(text)
    for name in sorted(names, key=len, reverse=True):
        remaining = re.sub(r"\b" + re.escape(normalize(name)) + r"\b", " ", remaining)
    remaining = re.sub(r"\b[ab]\d{3}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", " ", remaining)
    remaining = re.sub(r"(?<=ultimos )\d+|(?<=ultimo )\d+", " ", remaining)
    remaining = re.sub(
        r"\d+(?=\s+produtos)|(?<=top )\d+|(?<=ranking )\d+|(?<=ranking de )\d+", " ", remaining
    )
    if re.search(r"\d", remaining):
        return False
    words = set(re.findall(r"[a-z]+", remaining))
    allowed = set(
        "a as o os de da das do dos e em no nos na nas por para com um uma "
        "qual quais quanto quantos quantas foi foram tenho teve eu meu minha meus minhas "
        "vendi vendemos vendeu entrou vendido vendida vendidos vendidas vendas "
        "receita liquida liquido total faturamento pedidos pedido concluidos concluido ticket tiquete medio "
        "valor unidades unidade quantidade produtos produto ranking top maior maiores mais "
        "evolucao diaria diario diarias diarios dia dias ontem anteontem hoje ultimos ultimo "
        "sete trinta semana passada este nesse mes periodo anterior compare comparar "
        "comparado comparada comparacao versus vs mostre mostrar informe gostaria saber "
        "loja lojas toda todas centro jardins norte organizacao a b aurora brisa casa "
        "ate entre".split()
    )
    return words.issubset(allowed)
