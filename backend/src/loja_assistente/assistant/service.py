import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import QueryPlan, StoreScope
from loja_assistente.analytics.service import execute_query
from loja_assistente.assistant.contracts import Answer, AskRequest
from loja_assistente.assistant.interpretation import interpret_request
from loja_assistente.assistant.interpreters import demo, openai_adapter
from loja_assistente.assistant.presentation import describe
from loja_assistente.auth.service import (
    Principal,
    assert_store_access,
    permitted_stores,
    resolve_store_references,
)
from loja_assistente.config import settings
from loja_assistente.conversations.service import create_conversation, get_conversation
from loja_assistente.models import AnswerRecord, Operation, utcnow

logger = logging.getLogger("loja_assistente.operations")


def respond(db: Session, principal: Principal, request: AskRequest, request_id: str) -> Answer:
    start = perf_counter()
    interpretation_ms = 0
    query_ms = 0
    plan = None
    version = demo.VERSION if request.mode == "demo" else openai_adapter.VERSION
    try:
        if request.store_ids:
            assert_store_access(db, principal, request.store_ids)
        conversation = (
            get_conversation(db, principal, request.conversation_id, lock=True)
            if request.conversation_id
            else create_conversation(db, principal, request.question)
        )
    except HTTPException as error:
        record_operation(
            db,
            principal,
            request_id,
            request.mode,
            None,
            "conflict" if error.status_code == 409 else "denied",
            version,
            0,
            0,
            round((perf_counter() - start) * 1000),
        )
        db.commit()
        raise
    previous = QueryPlan.model_validate(conversation.last_plan) if conversation.last_plan else None
    stores = [StoreScope(id=store.id, name=store.name) for store in permitted_stores(db, principal)]
    answer = Answer(
        id=str(uuid4()),
        conversation_id=conversation.id,
        question=request.question,
        status="needs_clarification",
        message="",
        mode=request.mode,
        plan=None,
        result=None,
        request_id=request_id,
        created_at=utcnow(),
    )
    try:
        interpretation_start = perf_counter()
        interpreted = interpret_request(request, stores, settings.reference_date, previous)
        interpretation_ms = round((perf_counter() - interpretation_start) * 1000)
        answer.status = interpreted.status
        answer.message = interpreted.message
        if interpreted.plan:
            # Resolve first; execute_query independently checks the current grants again.
            scope = resolve_store_references(db, principal, interpreted.plan.store_references)
            plan = interpreted.plan.model_copy(
                update={"store_references": [store.id for store in scope]}
            )
            query_start = perf_counter()
            result = execute_query(db, principal, plan, request_id)
            query_ms = round((perf_counter() - query_start) * 1000)
            answer.plan, answer.result = plan, result
            answer.status = "no_data" if result.coverage.status == "absent" else "ready"
            answer.message = describe(result)
            conversation.last_plan = plan.model_dump(mode="json")
        if conversation.title == "Nova conversa":
            conversation.title = request.question[:120]
    except openai_adapter.ProviderUnavailable as error:
        interpretation_ms = round((perf_counter() - start) * 1000)
        answer.status = "provider_error"
        answer.message = str(error)
    except HTTPException as error:
        record_operation(
            db,
            principal,
            request_id,
            request.mode,
            plan,
            "conflict" if error.status_code == 409 else "denied",
            version,
            interpretation_ms,
            query_ms,
            round((perf_counter() - start) * 1000),
        )
        db.commit()
        raise
    db.add(
        AnswerRecord(
            id=answer.id,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            conversation_id=conversation.id,
            payload=answer.model_dump(mode="json"),
        )
    )
    record_operation(
        db,
        principal,
        request_id,
        request.mode,
        plan,
        answer.status,
        version,
        interpretation_ms,
        query_ms,
        round((perf_counter() - start) * 1000),
    )
    db.commit()
    return answer


def record_operation(
    db: Session,
    principal: Principal,
    request_id: str,
    mode: str,
    plan: QueryPlan | None,
    status: str,
    version: str,
    interpretation_ms: int,
    query_ms: int,
    response_ms: int,
) -> None:
    fields = {
        "request_id": request_id,
        "mode": mode,
        "capability": plan.intent if plan else None,
        "status": status,
        "interpreter_version": version,
        "interpretation_ms": interpretation_ms,
        "query_ms": query_ms,
        "response_ms": response_ms,
    }
    db.add(Operation(tenant_id=principal.tenant_id, user_id=principal.user_id, **fields))
    logger.info(json.dumps(fields))
