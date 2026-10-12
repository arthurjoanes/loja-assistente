from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import Principal, require_csrf
from loja_assistente.clarifications.contracts import (
    ClarificationMutation,
    ClarificationResponse,
    PendingClarification,
)
from loja_assistente.clarifications.service import cancel_clarification, respond_to_clarification
from loja_assistente.database import get_db

router = APIRouter(tags=["Esclarecimentos pessoais"])
Database = Annotated[Session, Depends(get_db)]
Identity = Annotated[Principal, Depends(require_csrf)]


@router.post("/conversations/{conversation_id}/clarification/respond")
def choose(
    conversation_id: str,
    body: ClarificationResponse,
    request: Request,
    db: Database,
    principal: Identity,
) -> Answer:
    return respond_to_clarification(db, principal, conversation_id, body, request.state.request_id)


@router.post("/conversations/{conversation_id}/clarification/cancel")
def cancel(
    conversation_id: str,
    body: ClarificationMutation,
    request: Request,
    db: Database,
    principal: Identity,
) -> PendingClarification:
    return cancel_clarification(db, principal, conversation_id, body, request.state.request_id)
