from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from loja_assistente.analytics.contracts import QueryPlan
from loja_assistente.analytics.service import execute_query
from loja_assistente.assistant.contracts import Answer
from loja_assistente.assistant.presentation import describe
from loja_assistente.auth.service import Principal, assert_store_access, resolve_store_references
from loja_assistente.conversations.service import create_conversation, get_answer
from loja_assistente.favorites.contracts import (
    LIST_LIMIT,
    SCHEMA_VERSION,
    Favorite,
    FavoriteRevisionRequest,
    RenameFavoriteRequest,
    SaveFavoriteRequest,
)
from loja_assistente.models import AnswerRecord, FavoriteRecord, Operation, utcnow

VERSION = "favorites-v1"


def validated_plan(db: Session, principal: Principal, record: FavoriteRecord) -> QueryPlan:
    if record.schema_version != SCHEMA_VERSION:
        raise HTTPException(status_code=409, detail="Formato do favorito incompatível. Recarregue.")
    try:
        plan = QueryPlan.model_validate(record.plan)
    except ValidationError as error:
        raise HTTPException(
            status_code=409, detail="Plano salvo inválido. Salve outro cálculo."
        ) from error
    # Saved scope is always explicit store IDs. Names and an empty scope cannot silently
    # expand a saved query when grants or store names change.
    stores = assert_store_access(db, principal, plan.store_references)
    return plan.model_copy(update={"store_references": [store.id for store in stores]})


def serialize_favorite(db: Session, principal: Principal, record: FavoriteRecord) -> Favorite:
    plan = validated_plan(db, principal, record)
    return Favorite(
        id=record.id,
        name=record.name,
        plan=plan,
        schema_version=SCHEMA_VERSION,
        source_answer_id=record.source_answer_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        revision=record.revision,
    )


def get_favorite(
    db: Session, principal: Principal, favorite_id: str, *, lock: bool = False
) -> FavoriteRecord:
    statement = select(FavoriteRecord).where(
        FavoriteRecord.id == favorite_id,
        FavoriteRecord.tenant_id == principal.tenant_id,
        FavoriteRecord.user_id == principal.user_id,
    )
    if lock:
        statement = statement.with_for_update(nowait=True)
    try:
        record = db.scalar(statement)
    except OperationalError as error:
        if getattr(error.orig, "sqlstate", None) != "55P03":
            raise
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Favorito ocupado. Aguarde e recarregue a lista."
        ) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Favorito não encontrado.")
    validated_plan(db, principal, record)
    return record


def list_favorites(db: Session, principal: Principal) -> list[Favorite]:
    records = db.scalars(
        select(FavoriteRecord)
        .where(
            FavoriteRecord.tenant_id == principal.tenant_id,
            FavoriteRecord.user_id == principal.user_id,
        )
        .order_by(FavoriteRecord.created_at.desc(), FavoriteRecord.id)
        .limit(LIST_LIMIT)
    )
    favorites: list[Favorite] = []
    for record in records:
        try:
            favorites.append(serialize_favorite(db, principal, record))
        except HTTPException as error:
            if error.status_code not in (403, 409):
                raise
            # Neither the user-supplied title nor the saved scope is safe to reveal
            # after revocation or failed validation.
    return favorites


def save_favorite(db: Session, principal: Principal, request: SaveFavoriteRequest) -> Favorite:
    try:
        answer = get_answer(db, principal, request.answer_id)
    except ValidationError as error:
        raise HTTPException(status_code=409, detail="Cálculo registrado inválido.") from error
    if answer.plan is None or answer.result is None or answer.status not in ("ready", "no_data"):
        raise HTTPException(status_code=422, detail="Salve uma resposta com cálculo válido.")
    scope = resolve_store_references(db, principal, answer.plan.store_references)
    # Legacy payloads may have represented all stores with an empty list. Preserve
    # the historical scope instead of copying today's potentially broader grants.
    if not answer.plan.store_references:
        scope = assert_store_access(db, principal, [store.id for store in answer.result.scope])
    plan = QueryPlan.model_validate(
        answer.plan.model_copy(
            update={"store_references": [store.id for store in scope]}
        ).model_dump()
    )
    now = utcnow()
    db.execute(
        insert(FavoriteRecord)
        .values(
            id=str(uuid4()),
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            name=request.name,
            plan=plan.model_dump(mode="json"),
            schema_version=SCHEMA_VERSION,
            source_answer_id=request.answer_id,
            created_at=now,
            updated_at=now,
            revision=1,
        )
        .on_conflict_do_nothing(constraint="uq_favorites_owner_source")
    )
    record = db.scalar(
        select(FavoriteRecord).where(
            FavoriteRecord.tenant_id == principal.tenant_id,
            FavoriteRecord.user_id == principal.user_id,
            FavoriteRecord.source_answer_id == request.answer_id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=409, detail="O favorito mudou. Recarregue e tente novamente."
        )
    favorite = serialize_favorite(db, principal, record)
    db.commit()
    return favorite


def require_revision(record: FavoriteRecord, revision: int) -> None:
    if record.revision != revision:
        raise HTTPException(
            status_code=409, detail="O favorito mudou em outra aba. Recarregue a lista."
        )


def rename_favorite(
    db: Session, principal: Principal, favorite_id: str, request: RenameFavoriteRequest
) -> Favorite:
    record = get_favorite(db, principal, favorite_id, lock=True)
    require_revision(record, request.revision)
    record.name = request.name
    record.revision += 1
    record.updated_at = utcnow()
    favorite = serialize_favorite(db, principal, record)
    db.commit()
    return favorite


def delete_favorite(
    db: Session, principal: Principal, favorite_id: str, request: FavoriteRevisionRequest
) -> None:
    record = get_favorite(db, principal, favorite_id, lock=True)
    require_revision(record, request.revision)
    db.delete(record)
    db.commit()


def run_favorite(
    db: Session,
    principal: Principal,
    favorite_id: str,
    request: FavoriteRevisionRequest,
    request_id: str,
) -> Answer:
    start = perf_counter()
    record = get_favorite(db, principal, favorite_id, lock=True)
    require_revision(record, request.revision)
    plan = validated_plan(db, principal, record)
    conversation = create_conversation(db, principal, record.name)
    query_start = perf_counter()
    result = execute_query(db, principal, plan, request_id)
    query_ms = round((perf_counter() - query_start) * 1000)
    answer = Answer(
        id=str(uuid4()),
        conversation_id=conversation.id,
        question=f"Consulta favorita: {record.name}",
        status="no_data" if result.coverage.status == "absent" else "ready",
        message=describe(result),
        mode="demo",
        plan=plan,
        result=result,
        request_id=request_id,
        created_at=utcnow(),
    )
    conversation.last_plan = plan.model_dump(mode="json")
    db.add(
        AnswerRecord(
            id=answer.id,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            conversation_id=conversation.id,
            payload=answer.model_dump(mode="json"),
            created_at=answer.created_at,
        )
    )
    db.add(
        Operation(
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            request_id=request_id,
            mode="demo",
            capability=plan.intent,
            status=answer.status,
            interpreter_version=VERSION,
            interpretation_ms=0,
            query_ms=query_ms,
            response_ms=round((perf_counter() - start) * 1000),
        )
    )
    # A successfully accepted execution consumes this revision, so a stale retry
    # cannot create another calculation. The UI must reload before another run.
    record.revision += 1
    record.updated_at = utcnow()
    db.commit()
    return answer
