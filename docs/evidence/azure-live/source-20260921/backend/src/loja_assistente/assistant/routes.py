from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import AnalyticsResult, QueryPlan
from loja_assistente.analytics.service import execute_query
from loja_assistente.assistant.contracts import Answer, AskRequest
from loja_assistente.assistant.service import respond
from loja_assistente.auth.service import Principal, require_csrf
from loja_assistente.database import get_db

router = APIRouter(tags=["Consultas"])
Database = Annotated[Session, Depends(get_db)]
Identity = Annotated[Principal, Depends(require_csrf)]


@router.post("/assistant/query")
def ask(body: AskRequest, request: Request, db: Database, principal: Identity) -> Answer:
    return respond(db, principal, body, request.state.request_id)


@router.post("/analytics/query")
def structured_query(
    body: QueryPlan, request: Request, db: Database, principal: Identity
) -> AnalyticsResult:
    return execute_query(db, principal, body, request.state.request_id)
