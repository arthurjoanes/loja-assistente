from datetime import date, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Period(StrictModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if not 1 <= (self.end - self.start).days <= 90:
            raise ValueError("Use 1 a 90 dias, com fim exclusivo.")
        return self


class QueryPlan(StrictModel):
    intent: Literal["aggregate", "ranking", "daily"]
    metric: Literal["revenue", "orders", "average_ticket", "units"]
    store_references: list[str] = Field(default_factory=list, max_length=6)
    period: Period
    comparison: Literal["previous_period"] | None = None
    grouping: Literal["day"] | None = None
    limit: int = Field(default=5, ge=1, le=20, strict=True)

    @model_validator(mode="after")
    def validate_capability(self) -> Self:
        if self.comparison:
            try:
                self.period.start - timedelta(days=(self.period.end - self.period.start).days)
            except OverflowError as error:
                raise ValueError("A comparação ultrapassa a menor data válida.") from error
        if self.intent == "ranking" and self.metric not in ("revenue", "units"):
            raise ValueError("Ranking aceita receita ou unidades.")
        if self.intent == "daily" and self.grouping != "day":
            raise ValueError("Evolução diária exige agrupamento day.")
        if self.intent != "daily" and self.grouping is not None:
            raise ValueError("Agrupamento só se aplica à evolução diária.")
        if any(not ref.strip() or len(ref) > 120 for ref in self.store_references):
            raise ValueError("Referência de loja inválida.")
        return self


class StoreScope(StrictModel):
    id: str
    name: str


class Totals(StrictModel):
    revenue_cents: int
    orders: int
    units: int
    average_ticket_cents: str | None

    @field_serializer("revenue_cents", when_used="json")
    def serialize_revenue(self, value: int) -> str:
        # Keep Python arithmetic exact and accept integer values in older saved answers.
        return str(value)


class ResultRow(Totals):
    key: str
    label: str


class MissingDay(StrictModel):
    store_id: str
    date: date


class CoverageResult(StrictModel):
    status: Literal["complete", "partial", "absent"]
    covered_days: int
    expected_days: int
    missing: list[MissingDay]


class Comparison(StrictModel):
    period: Period
    value: str | None
    change_percent: str | None
    message: str


class AnalyticsResult(StrictModel):
    intent: Literal["aggregate", "ranking", "daily"]
    metric: Literal["revenue", "orders", "average_ticket", "units"]
    scope: list[StoreScope]
    period: Period
    timezone: str
    currency: str
    unit: str
    formula: str
    value: str | None
    totals: Totals | None
    rows: list[ResultRow]
    coverage: CoverageResult
    comparison: Comparison | None
    evidence: list[ResultRow]
    dataset_version: str
    request_id: str
