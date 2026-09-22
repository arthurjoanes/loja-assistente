from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import QueryPlan
from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import (
    Principal,
    assert_store_access,
    permitted_stores,
    resolve_store_references,
)
from loja_assistente.models import AnswerRecord, Conversation


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[Answer]


def get_conversation(
    db: Session, principal: Principal, conversation_id: str, *, lock: bool = False
) -> Conversation:
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == principal.tenant_id,
        Conversation.user_id == principal.user_id,
    )
    if lock:
        statement = statement.with_for_update(nowait=True)
    try:
        conversation = db.scalar(statement)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) != "55P03":
            raise
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conversa ocupada. Aguarde a resposta e tente novamente.",
        ) from error
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    allowed = sorted(store.id for store in permitted_stores(db, principal))
    revoked_answer = db.scalar(
        select(AnswerRecord.id)
        .where(
            AnswerRecord.conversation_id == conversation.id,
            AnswerRecord.tenant_id == principal.tenant_id,
            AnswerRecord.user_id == principal.user_id,
            ~AnswerRecord.payload["plan"]["store_references"].contained_by(allowed),
        )
        .limit(1)
    )
    if revoked_answer:
        raise HTTPException(
            status_code=403, detail="Uma loja desta conversa não está mais autorizada."
        )
    if conversation.last_plan:
        resolve_store_references(
            db, principal, QueryPlan.model_validate(conversation.last_plan).store_references
        )
    return conversation


def summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id, title=conversation.title, created_at=conversation.created_at
    )


def create_conversation(
    db: Session, principal: Principal, title: str = "Nova conversa"
) -> Conversation:
    conversation = Conversation(
        tenant_id=principal.tenant_id, user_id=principal.user_id, title=title[:120]
    )
    db.add(conversation)
    db.flush()
    return conversation


def validate_answer_access(db: Session, principal: Principal, record: AnswerRecord) -> Answer:
    answer = Answer.model_validate(record.payload)
    if answer.result:
        assert_store_access(db, principal, [store.id for store in answer.result.scope])
    if answer.plan:
        resolve_store_references(db, principal, answer.plan.store_references)
    return answer


def get_answer(db: Session, principal: Principal, answer_id: str) -> Answer:
    record = db.scalar(
        select(AnswerRecord).where(
            AnswerRecord.id == answer_id,
            AnswerRecord.tenant_id == principal.tenant_id,
            AnswerRecord.user_id == principal.user_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Resposta não encontrada.")
    return validate_answer_access(db, principal, record)
