from datetime import date

from openai import OpenAI

from loja_assistente.analytics.contracts import QueryPlan, StoreScope
from loja_assistente.assistant.contracts import AskRequest, Interpretation
from loja_assistente.assistant.filter_limits import unsupported_filter
from loja_assistente.assistant.interpreters import demo, openai_adapter
from loja_assistente.config import settings


def interpret_request(
    request: AskRequest, stores: list[StoreScope], reference_date: date, previous: QueryPlan | None
) -> Interpretation:
    unsupported = unsupported_filter(request.question)
    if unsupported:
        interpreted = Interpretation(status="needs_clarification", plan=None, message=unsupported)
    elif request.mode == "demo":
        interpreted = demo.interpret(
            request.question,
            stores,
            reference_date,
            previous,
            request.period,
            request.store_ids,
        )
    else:
        if not settings.llm_enabled or not settings.openai_api_key:
            raise openai_adapter.ProviderUnavailable(
                "Modo LLM não configurado. Defina OPENAI_API_KEY e LLM_ENABLED no servidor, ou selecione demo."
            )
        with OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=12.0,
            max_retries=0,
        ) as client:
            interpreted = openai_adapter.interpret(
                request.question,
                stores,
                reference_date,
                previous,
                request.period,
                request.store_ids,
                client=client,
                model=settings.openai_model,
                reasoning_effort=settings.openai_reasoning_effort,
            )
    return interpreted
