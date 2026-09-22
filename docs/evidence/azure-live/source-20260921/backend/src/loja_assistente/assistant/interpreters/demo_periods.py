"Períodos e comparações do modo demo."

import re
from datetime import date, timedelta
from typing import Literal

from loja_assistente.analytics.contracts import Period, QueryPlan


def continuation_plan(text: str, previous: QueryPlan | None) -> QueryPlan | None:
    matched = re.fullmatch(r"e (?:nos?|nas?) (?:sete|7|\d+)?\s*dias? anteriores\??", text)
    if not matched and text not in ("e no periodo anterior?", "e no periodo anterior"):
        return None
    if previous is None:
        raise ValueError("Faça uma consulta com indicador e período antes de continuar.")
    count = re.search(r"(\d+|sete)", text)
    days = (
        (7 if count.group() == "sete" else int(count.group()))
        if count
        else (previous.period.end - previous.period.start).days
    )
    if not 1 <= days <= 90:
        raise ValueError("Escolha um período entre 1 e 90 dias.")
    if previous.period.start.toordinal() <= days:
        raise ValueError("O período anterior ultrapassa a menor data válida.")
    return previous.model_copy(
        update={
            "period": Period(
                start=previous.period.start - timedelta(days=days), end=previous.period.start
            ),
            "comparison": None,
        }
    )


def select_period(
    text: str, reference: date, selected: Period | None
) -> tuple[Period, Literal["previous_period"] | None]:
    comparison = bool(re.search(r"\b(?:compar\w*|versus|vs)\b", text))
    if comparison:
        if "anterior" not in text and "anteontem" not in text:
            raise ValueError(
                "Compare com o período anterior de mesma duração. Ex.: compare a receita dos últimos 7 dias com o período anterior."
            )
        if "anteontem" in text:
            if not re.search(r"\bontem\b", text):
                raise ValueError("Para comparar com anteontem, consulte a receita de ontem.")
            text = text.replace("anteontem", "")
    elif "anterior" in text:
        raise ValueError("Para comparar, informe o período ou use a continuação da conversa.")
    elif "anteontem" in text and re.search(r"\bontem\b", text):
        raise ValueError(
            "Deseja um intervalo de dois dias ou uma comparação entre ontem e anteontem?"
        )
    try:
        period = parse_period(text, reference) or selected
    except (ValueError, OverflowError) as error:
        raise ValueError("Use 1 a 90 dias. Ex.: de 2026-08-10 a 2026-08-16.") from error
    if period is None:
        raise ValueError("Qual período? Ex.: ontem, últimos 7 dias ou de 2026-08-10 a 2026-08-16.")
    return period, "previous_period" if comparison else None


def parse_period(text: str, reference: date) -> Period | None:
    dates = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", text)
    if len(dates) > 2:
        raise ValueError("Datas demais")
    relative_periods = re.findall(
        r"\b(?:anteontem|ontem|hoje|ultimos?\s+(?:\d+|sete|trinta)\s+dias?"
        r"|semana passada|(?:este|nesse) mes)\b",
        text,
    )
    if len(relative_periods) > 1 or (dates and relative_periods):
        raise ValueError("Mais de um período na mesma consulta")
    if dates:
        parsed = [
            date.fromisoformat(value)
            if "-" in value
            else date.fromisoformat("-".join(reversed(value.split("/"))))
            for value in dates
        ]
        return Period(start=parsed[0], end=parsed[-1] + timedelta(days=1))
    if "anteontem" in text:
        return Period(start=reference - timedelta(days=2), end=reference - timedelta(days=1))
    if "ontem" in text:
        return Period(start=reference - timedelta(days=1), end=reference)
    if "hoje" in text:
        return Period(start=reference, end=reference + timedelta(days=1))
    number = re.search(r"ultimos?\s+(\d+|sete|trinta)\s+dias?", text)
    if number:
        value = number.group(1)
        days = {"sete": 7, "trinta": 30}.get(value, int(value) if value.isdigit() else 0)
        if not 1 <= days <= 90:
            raise ValueError("Período fora do limite")
        return Period(start=reference - timedelta(days=days), end=reference)
    if "semana passada" in text:
        monday = reference - timedelta(days=reference.weekday())
        return Period(start=monday - timedelta(days=7), end=monday)
    if "este mes" in text or "nesse mes" in text:
        return Period(start=reference.replace(day=1), end=reference)
    return None
