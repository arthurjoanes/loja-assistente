from datetime import date, datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from loja_assistente.analytics.contracts import Period, QueryPlan, StrictModel


class PartialPlan(StrictModel):
    """Resolved domain fields, deliberately distinct from an executable QueryPlan."""

    intent: Literal["aggregate", "ranking", "daily"]
    metric: Literal["revenue", "orders", "average_ticket", "units"]
    store_ids: list[str] = Field(max_length=6)
    period: Period | None = None
    comparison: Literal["previous_period"] | None = None
    grouping: Literal["day"] | None = None
    limit: int = Field(default=5, ge=1, le=20, strict=True)

    @model_validator(mode="after")
    def validate_resolved_fields(self) -> Self:
        if self.intent == "ranking" and self.metric not in ("revenue", "units"):
            raise ValueError("Ranking aceita receita ou unidades.")
        if (self.intent == "daily") != (self.grouping == "day"):
            raise ValueError("Agrupamento day só se aplica à evolução diária.")
        if any(not value.strip() or len(value) > 64 for value in self.store_ids):
            raise ValueError("Identificador de loja inválido.")
        if len(set(self.store_ids)) != len(self.store_ids):
            raise ValueError("Identificadores de loja repetidos.")
        return self

    def executable(self) -> QueryPlan:
        if self.period is None or not self.store_ids:
            raise ValueError("O plano ainda precisa de período e lojas resolvidos.")
        return QueryPlan(
            intent=self.intent,
            metric=self.metric,
            store_references=self.store_ids,
            period=self.period,
            comparison=self.comparison,
            grouping=self.grouping,
            limit=self.limit,
        )


class ClarificationChoice(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=300)
    period: Period | None = None
    store_ids: list[str] | None = Field(default=None, max_length=6)

    @model_validator(mode="after")
    def exactly_one_field(self) -> Self:
        if (self.period is None) == (self.store_ids is None):
            raise ValueError("A escolha deve resolver exatamente um campo.")
        if self.store_ids is not None and (
            not self.store_ids
            or any(not value.strip() or len(value) > 64 for value in self.store_ids)
            or len(set(self.store_ids)) != len(self.store_ids)
        ):
            raise ValueError("Escolha de loja inválida.")
        return self


class ClarificationDraft(StrictModel):
    partial_plan: PartialPlan
    missing_field: Literal["period", "store"]
    choices: list[ClarificationChoice] = Field(default_factory=list, max_length=6)


class PendingClarification(StrictModel):
    id: str
    revision: int = Field(ge=1, strict=True)
    status: Literal["pending", "resolved", "cancelled", "expired"]
    original_question: str = Field(min_length=1, max_length=1000)
    partial_plan: PartialPlan
    missing_field: Literal["period", "store"]
    choices: list[ClarificationChoice] = Field(min_length=1, max_length=6)
    created_at: datetime
    expires_at: datetime
    schema_version: Literal[1] = 1
    mode: Literal["demo", "llm"]
    reference_date: date

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("Instantes de esclarecimento precisam de fuso horário.")
        if self.expires_at <= self.created_at:
            raise ValueError("Expiração inválida.")
        if len({choice.id for choice in self.choices}) != len(self.choices):
            raise ValueError("Identificadores de escolha repetidos.")
        if any(
            (self.missing_field == "period") != (choice.period is not None)
            for choice in self.choices
        ):
            raise ValueError("Escolhas não correspondem ao campo solicitado.")
        if (
            self.status == "pending"
            and self.missing_field == "period"
            and self.partial_plan.period is not None
        ):
            raise ValueError("O período solicitado já está resolvido.")
        return self


class ClarificationMutation(StrictModel):
    pending_id: str = Field(min_length=1, max_length=36)
    revision: int = Field(ge=1, strict=True)


class ClarificationResponse(ClarificationMutation):
    choice_id: str = Field(min_length=1, max_length=64)


class ClarificationSelection(StrictModel):
    pending_id: str
    revision: int = Field(ge=1, strict=True)
    choice_id: str
    label: str
