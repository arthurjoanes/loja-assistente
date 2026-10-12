from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from loja_assistente.analytics.contracts import QueryPlan, StrictModel

SCHEMA_VERSION: Literal[1] = 1
LIST_LIMIT = 50


class FavoriteName(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(character) < 32 for character in value):
            raise ValueError("Use um nome de 1 a 120 caracteres, sem caracteres de controle.")
        return value


class SaveFavoriteRequest(FavoriteName):
    answer_id: str = Field(min_length=1, max_length=64)


class FavoriteRevisionRequest(StrictModel):
    revision: int = Field(ge=1, strict=True)


class RenameFavoriteRequest(FavoriteName, FavoriteRevisionRequest):
    pass


class Favorite(StrictModel):
    id: str
    name: str
    plan: QueryPlan
    schema_version: Literal[1]
    source_answer_id: str
    created_at: datetime
    updated_at: datetime
    revision: int = Field(ge=1)
