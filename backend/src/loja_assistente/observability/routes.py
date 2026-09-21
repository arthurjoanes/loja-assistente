from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.auth.service import Principal, get_principal
from loja_assistente.database import get_db
from loja_assistente.models import Operation

router = APIRouter(tags=["Operação pessoal"])


class OperationEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    request_id: str
    mode: str
    capability: str | None
    status: str
    interpretation_ms: int
    query_ms: int
    response_ms: int
    interpreter_version: str
    created_at: datetime


class OperationsResponse(BaseModel):
    entries: list[OperationEntry]
    total: int
    errors: int
    tokens: None = None
    cost: None = None


@router.get("/operations")
def operations(
    db: Annotated[Session, Depends(get_db)], principal: Annotated[Principal, Depends(get_principal)]
) -> OperationsResponse:
    entries = [
        OperationEntry.model_validate(row)
        for row in db.scalars(
            select(Operation)
            .where(
                Operation.tenant_id == principal.tenant_id,
                Operation.user_id == principal.user_id,
            )
            .order_by(Operation.created_at.desc())
            .limit(100)
        )
    ]
    return OperationsResponse(
        entries=entries,
        total=len(entries),
        errors=sum(
            entry.status in ("provider_error", "denied", "error", "conflict") for entry in entries
        ),
    )
