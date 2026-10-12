from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from loja_assistente.analytics.service import execute_query
from loja_assistente.assistant.contracts import Answer
from loja_assistente.assistant.presentation import describe
from loja_assistente.assistant.service import persist_answer, record_operation
from loja_assistente.auth.service import Principal, assert_store_access
from loja_assistente.clarifications.contracts import (
    ClarificationDraft,
    ClarificationMutation,
    ClarificationResponse,
    ClarificationSelection,
    PartialPlan,
    PendingClarification,
)
from loja_assistente.clarifications.state import (
    CLARIFICATION_VERSION,
    create_pending,
    read_pending,
    revise_pending,
    write_pending,
)
from loja_assistente.conversations.service import get_conversation
from loja_assistente.models import Conversation, utcnow


def current_pending(
    db: Session,
    principal: Principal,
    conversation_id: str,
    mutation: ClarificationMutation,
) -> tuple[Conversation, PendingClarification]:
    conversation = get_conversation(db, principal, conversation_id, lock=True)
    pending = read_pending(conversation)
    if pending and pending.status == "expired":
        revise_pending(conversation, "expired")
        db.commit()
        raise HTTPException(
            status_code=409, detail="Esclarecimento expirado. Faça uma nova pergunta."
        )
    if (
        pending is None
        or pending.status != "pending"
        or pending.id != mutation.pending_id
        or pending.revision != mutation.revision
    ):
        raise HTTPException(
            status_code=409,
            detail="Esta escolha ficou desatualizada. Recarregue a conversa antes de continuar.",
        )
    return conversation, pending


def respond_to_clarification(
    db: Session,
    principal: Principal,
    conversation_id: str,
    mutation: ClarificationResponse,
    request_id: str,
) -> Answer:
    started = perf_counter()
    query_ms = 0
    plan = None
    mode = "demo"
    try:
        conversation, pending = current_pending(db, principal, conversation_id, mutation)
        mode = pending.mode
        choice = next((item for item in pending.choices if item.id == mutation.choice_id), None)
        if choice is None:
            raise HTTPException(
                status_code=409, detail="Escolha desatualizada. Recarregue a conversa."
            )
        resolved = PartialPlan.model_validate(
            {
                **pending.partial_plan.model_dump(),
                pending.missing_field
                if pending.missing_field == "period"
                else "store_ids": choice.period
                if pending.missing_field == "period"
                else choice.store_ids,
            }
        )
        assert_store_access(db, principal, resolved.store_ids)
        answer = Answer(
            id=str(uuid4()),
            conversation_id=conversation.id,
            question=pending.original_question,
            status="needs_clarification",
            message="Qual período deseja consultar? O indicador e as lojas serão preservados.",
            mode=pending.mode,
            plan=None,
            result=None,
            request_id=request_id,
            created_at=utcnow(),
            clarification_response=ClarificationSelection(
                pending_id=pending.id,
                revision=pending.revision,
                choice_id=choice.id,
                label=choice.label,
            ),
        )
        if resolved.period is None:
            # A store choice may leave the period missing; no interpreter or provider is called.
            answer.pending_clarification = create_pending(
                db,
                principal,
                conversation,
                ClarificationDraft(partial_plan=resolved, missing_field="period"),
                pending.original_question,
                pending.mode,
                pending.reference_date,
            )
        else:
            plan = resolved.executable()
            query_started = perf_counter()
            result = execute_query(db, principal, plan, request_id)
            query_ms = round((perf_counter() - query_started) * 1000)
            answer.plan, answer.result = plan, result
            answer.status = "no_data" if result.coverage.status == "absent" else "ready"
            answer.message = describe(result)
            conversation.last_plan = plan.model_dump(mode="json")
            answer.pending_clarification = PendingClarification.model_validate(
                {
                    **pending.model_dump(),
                    "revision": conversation.clarification_revision + 1,
                    "status": "resolved",
                    "partial_plan": resolved,
                }
            )
            write_pending(conversation, answer.pending_clarification)
        persist_answer(db, principal, answer)
        record_operation(
            db,
            principal,
            request_id,
            mode,
            plan,
            answer.status,
            CLARIFICATION_VERSION,
            0,
            query_ms,
            round((perf_counter() - started) * 1000),
        )
        db.commit()
        return answer
    except (ValidationError, ValueError) as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Plano de esclarecimento inválido. Faça uma nova conversa."
        ) from error
    except HTTPException as error:
        record_operation(
            db,
            principal,
            request_id,
            mode,
            None,
            "conflict" if error.status_code == 409 else "denied",
            CLARIFICATION_VERSION,
            0,
            0,
            round((perf_counter() - started) * 1000),
        )
        db.commit()
        raise


def cancel_clarification(
    db: Session,
    principal: Principal,
    conversation_id: str,
    mutation: ClarificationMutation,
    request_id: str,
) -> PendingClarification:
    conversation, pending = current_pending(db, principal, conversation_id, mutation)
    cancelled = revise_pending(conversation, "cancelled")
    assert cancelled is not None
    record_operation(
        db, principal, request_id, pending.mode, None, "cancelled", CLARIFICATION_VERSION, 0, 0, 0
    )
    db.commit()
    return cancelled
