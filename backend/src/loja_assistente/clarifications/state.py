from datetime import date, timedelta
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import Period
from loja_assistente.auth.service import Principal, assert_store_access
from loja_assistente.clarifications.contracts import (
    ClarificationChoice,
    ClarificationDraft,
    PendingClarification,
)
from loja_assistente.models import Conversation, utcnow

CLARIFICATION_VERSION = "clarification-state-v1"
CLARIFICATION_TTL = timedelta(minutes=30)


def read_pending(conversation: Conversation) -> PendingClarification | None:
    if conversation.pending_clarification is None:
        return None
    try:
        pending = PendingClarification.model_validate(conversation.pending_clarification)
    except ValidationError as error:
        raise HTTPException(
            status_code=409, detail="Esclarecimento incompatível. Faça uma nova conversa."
        ) from error
    if pending.revision != conversation.clarification_revision:
        raise HTTPException(
            status_code=409, detail="Esclarecimento desatualizado. Recarregue a conversa."
        )
    if pending.status == "pending" and pending.expires_at <= utcnow():
        return pending.model_copy(update={"status": "expired"})
    return pending


def pending_store_ids(pending: PendingClarification) -> list[str]:
    return sorted(
        set(pending.partial_plan.store_ids).union(
            *(choice.store_ids or [] for choice in pending.choices)
        )
    )


def validate_pending_access(
    db: Session, principal: Principal, pending: PendingClarification
) -> None:
    # Even unchosen options may describe private stores, so authorize the whole payload.
    assert_store_access(db, principal, pending_store_ids(pending))


def write_pending(conversation: Conversation, pending: PendingClarification) -> None:
    conversation.clarification_revision = pending.revision
    conversation.pending_clarification = pending.model_dump(mode="json")


def revise_pending(
    conversation: Conversation, status: str | None = None
) -> PendingClarification | None:
    pending = read_pending(conversation)
    if pending is None:
        return None
    revised = PendingClarification.model_validate(
        {
            **pending.model_dump(),
            "revision": conversation.clarification_revision + 1,
            "status": status or pending.status,
        }
    )
    write_pending(conversation, revised)
    return revised


def period_choices(reference: date) -> list[ClarificationChoice]:
    return [
        ClarificationChoice(
            id=choice_id,
            label=label,
            period=Period(start=reference - timedelta(days=days), end=reference),
        )
        for choice_id, label, days in (
            ("yesterday", "Ontem", 1),
            ("last_7_days", "Últimos 7 dias", 7),
            ("last_30_days", "Últimos 30 dias", 30),
        )
    ]


def create_pending(
    db: Session,
    principal: Principal,
    conversation: Conversation,
    draft: ClarificationDraft,
    question: str,
    mode: str,
    reference: date,
) -> PendingClarification:
    now = utcnow()
    pending = PendingClarification.model_validate(
        {
            "id": str(uuid4()),
            "revision": conversation.clarification_revision + 1,
            "status": "pending",
            "original_question": question,
            "partial_plan": draft.partial_plan,
            "missing_field": draft.missing_field,
            "choices": period_choices(reference)
            if draft.missing_field == "period"
            else draft.choices,
            "created_at": now,
            "expires_at": now + CLARIFICATION_TTL,
            "schema_version": 1,
            "mode": mode,
            "reference_date": reference,
        }
    )
    validate_pending_access(db, principal, pending)
    write_pending(conversation, pending)
    return pending
