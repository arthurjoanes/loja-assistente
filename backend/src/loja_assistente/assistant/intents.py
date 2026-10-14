"""A committed admission survives a lost response or an uncertain provider result."""

import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from loja_assistente.assistant.contracts import Answer, AskRequest
from loja_assistente.auth.service import Principal
from loja_assistente.conversations.service import get_answer
from loja_assistente.models import QueryIntent, utcnow


def identity(principal: Principal, key: str) -> tuple[str, str, str]:
    return principal.tenant_id, principal.user_id, key


def recover(db: Session, principal: Principal, key: str) -> Answer:
    intent = db.get(QueryIntent, identity(principal, key))
    if intent is None:
        raise HTTPException(404, "Intenção não encontrada.")
    if intent.answer_id is None:
        raise HTTPException(
            409,
            "A execução ainda não foi confirmada. Nenhuma nova chamada foi feita; consulte o histórico ou recupere esta intenção novamente.",
        )
    return get_answer(db, principal, intent.answer_id)


def admit(db: Session, principal: Principal, body: AskRequest) -> tuple[QueryIntent, bool]:
    assert body.client_request_id is not None
    digest = hashlib.sha256(
        json.dumps(
            body.model_dump(mode="json", exclude={"client_request_id"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    # This commit must precede any provider invocation. A crashed owner is never retried.
    with Session(db.get_bind()) as admission:
        created = admission.execute(
            insert(QueryIntent)
            .values(
                tenant_id=principal.tenant_id,
                user_id=principal.user_id,
                client_request_id=body.client_request_id,
                fingerprint=digest,
                request_id=str(uuid4()),
                created_at=utcnow(),
            )
            .on_conflict_do_nothing()
            .returning(QueryIntent.request_id)
        ).scalar_one_or_none()
        admission.commit()
    intent = db.get(QueryIntent, identity(principal, body.client_request_id))
    assert intent is not None
    if intent.fingerprint != digest:
        raise HTTPException(409, "Esta intenção já identifica uma pergunta com outro conteúdo.")
    return intent, created is not None
