from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import AnalyticsResult, StrictModel
from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import Principal, get_principal, permitted_stores, require_csrf
from loja_assistente.conversations.pagination import decode, encode, older
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
    return conversation_page(db, principal)["items"]


@router.get("/conversations/page")
def conversation_page(db: Database, principal: Identity, cursor: str | None = None) -> dict:
    after = decode(principal, "conversations", cursor)
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
    visible = []
    # Fill the visible page, rather than limiting first and silently dropping revoked rows.
    while len(visible) <= 50:
        candidates = list(
            db.scalars(
                select(Conversation)
                .where(
                    Conversation.tenant_id == principal.tenant_id,
                    Conversation.user_id == principal.user_id,
                    ~revoked_history,
                    older(Conversation, after),
                )
                .order_by(Conversation.created_at.desc(), Conversation.id.desc())
                .limit(51)
            )
        )
        if not candidates:
            break
        for conversation in candidates:
            after = (conversation.created_at, conversation.id)
            try:
                get_conversation(db, principal, conversation.id)
            except HTTPException as error:
                if error.status_code not in (403, 409):
                    raise
                continue
            visible.append(summary(conversation))
            if len(visible) > 50:
                break
        if len(candidates) < 51:
            break
    more = len(visible) > 50
    items = visible[:50]
    return {
        "items": items,
        "has_more": more,
        "next_cursor": encode(principal, "conversations", items[-1].created_at, items[-1].id)
        if more
        else None,
    }


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
    messages = message_page(conversation_id, db, principal)
    return ConversationDetail(
        **summary(conversation).model_dump(),
        messages=messages["items"],
        messages_next_cursor=messages["next_cursor"],
    )


@router.get("/conversations/{conversation_id}/messages")
def message_page(
    conversation_id: str, db: Database, principal: Identity, cursor: str | None = None
) -> dict:
    get_conversation(db, principal, conversation_id)
    scope = "messages:" + conversation_id
    after = decode(principal, scope, cursor)
    records = list(
        db.scalars(
            select(AnswerRecord)
            .where(
                AnswerRecord.conversation_id == conversation_id,
                AnswerRecord.tenant_id == principal.tenant_id,
                AnswerRecord.user_id == principal.user_id,
                older(AnswerRecord, after),
            )
            .order_by(AnswerRecord.created_at.desc(), AnswerRecord.id.desc())
            .limit(101)
        )
    )
    more = len(records) > 100
    records = records[:100]
    messages = [validate_answer_access(db, principal, record) for record in records]
    return {
        "items": list(reversed(messages)),
        "has_more": more,
        "next_cursor": encode(principal, scope, records[-1].created_at, records[-1].id)
        if more
        else None,
    }


@router.get("/answers/{answer_id}")
def answer_detail(answer_id: str, db: Database, principal: Identity) -> Answer:
    return get_answer(db, principal, answer_id)


@router.get("/answers/{answer_id}/evidence")
def answer_evidence(answer_id: str, db: Database, principal: Identity) -> AnalyticsResult:
    answer = get_answer(db, principal, answer_id)
    if answer.result is None:
        raise HTTPException(status_code=404, detail="Esta resposta não executou uma consulta.")
    return answer.result
