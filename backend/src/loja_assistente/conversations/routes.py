from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import AnalyticsResult, StrictModel
from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import Principal, get_principal, permitted_stores, require_csrf
from loja_assistente.conversations.service import (
    ConversationDetail,
    ConversationSummary,
    create_conversation,
    get_answer,
    get_conversation,
    summary,
    validate_answer_access,
)
from loja_assistente.database import get_db
from loja_assistente.models import AnswerRecord, Conversation

router = APIRouter(tags=["Conversas pessoais"])
Database = Annotated[Session, Depends(get_db)]
Identity = Annotated[Principal, Depends(get_principal)]
MutationIdentity = Annotated[Principal, Depends(require_csrf)]


class EmptyBody(StrictModel):
    pass


@router.get("/conversations")
def list_conversations(db: Database, principal: Identity) -> list[ConversationSummary]:
    conversations = db.scalars(
        select(Conversation)
        .where(
            Conversation.tenant_id == principal.tenant_id,
            Conversation.user_id == principal.user_id,
        )
        .order_by(Conversation.created_at.desc())
        .limit(50)
    )
    allowed = {store.id for store in permitted_stores(db, principal)}
    # Every persisted plan matters: the title may describe an earlier, now revoked store.
    revoked_history = (
        select(AnswerRecord.id)
        .where(
            AnswerRecord.conversation_id == Conversation.id,
            AnswerRecord.tenant_id == principal.tenant_id,
            AnswerRecord.user_id == principal.user_id,
            ~AnswerRecord.payload["plan"]["store_references"].contained_by(sorted(allowed)),
        )
        .exists()
    )
    hidden_ids = set(
        db.scalars(
            select(Conversation.id).where(
                Conversation.tenant_id == principal.tenant_id,
                Conversation.user_id == principal.user_id,
                revoked_history,
            )
        )
    )
    return [
        summary(conversation)
        for conversation in conversations
        if conversation.id not in hidden_ids
        and (
            not conversation.last_plan
            or set(conversation.last_plan["store_references"]).issubset(allowed)
        )
    ]


@router.post("/conversations")
def new_conversation(
    body: EmptyBody, db: Database, principal: MutationIdentity
) -> ConversationSummary:
    conversation = create_conversation(db, principal)
    db.commit()
    return summary(conversation)


@router.get("/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str, db: Database, principal: Identity
) -> ConversationDetail:
    conversation = get_conversation(db, principal, conversation_id)
    records = db.scalars(
        select(AnswerRecord)
        .where(
            AnswerRecord.conversation_id == conversation_id,
            AnswerRecord.tenant_id == principal.tenant_id,
            AnswerRecord.user_id == principal.user_id,
        )
        .order_by(AnswerRecord.created_at.desc())
        .limit(100)
    )
    messages = [validate_answer_access(db, principal, record) for record in records]
    return ConversationDetail(
        **summary(conversation).model_dump(), messages=list(reversed(messages))
    )


@router.get("/answers/{answer_id}")
def answer_detail(answer_id: str, db: Database, principal: Identity) -> Answer:
    return get_answer(db, principal, answer_id)


@router.get("/answers/{answer_id}/evidence")
def answer_evidence(answer_id: str, db: Database, principal: Identity) -> AnalyticsResult:
    answer = get_answer(db, principal, answer_id)
    if answer.result is None:
        raise HTTPException(status_code=404, detail="Esta resposta não executou uma consulta.")
    return answer.result
