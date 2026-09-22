from datetime import datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from loja_assistente.analytics.contracts import AnalyticsResult, Period, QueryPlan, StrictModel


class Interpretation(StrictModel):
    status: Literal["ready", "needs_clarification", "unsupported"]
    plan: QueryPlan | None
    message: str = Field(max_length=600)

    @model_validator(mode="after")
    def require_executable_plan(self) -> Self:
        if (self.status == "ready") != (self.plan is not None):
            raise ValueError("Apenas o estado ready deve conter um plano.")
        return self


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, max_length=36)
    mode: Literal["demo", "llm"] = "demo"
    store_ids: list[str] = Field(default_factory=list, max_length=6)
    period: Period | None = None

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Escreva uma pergunta.")
        return value

    @field_validator("store_ids")
    @classmethod
    def valid_store_identifiers(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 64 for value in values):
            raise ValueError("Identificador de loja inválido.")
        return list(dict.fromkeys(values))


class Answer(StrictModel):
    id: str
    conversation_id: str
    question: str
    status: Literal["ready", "needs_clarification", "unsupported", "provider_error", "no_data"]
    message: str
    mode: Literal["demo", "llm"]
    plan: QueryPlan | None
    result: AnalyticsResult | None
    request_id: str
    created_at: datetime
