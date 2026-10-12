from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from loja_assistente.assistant.contracts import Answer
from loja_assistente.auth.service import Principal, get_principal, require_csrf
from loja_assistente.database import get_db
from loja_assistente.favorites.contracts import (
    Favorite,
    FavoriteRevisionRequest,
    RenameFavoriteRequest,
    SaveFavoriteRequest,
)
from loja_assistente.favorites.service import (
    delete_favorite,
    get_favorite,
    list_favorites,
    rename_favorite,
    run_favorite,
    save_favorite,
    serialize_favorite,
)

router = APIRouter(tags=["Consultas favoritas"])
Database = Annotated[Session, Depends(get_db)]
Identity = Annotated[Principal, Depends(get_principal)]
MutationIdentity = Annotated[Principal, Depends(require_csrf)]


@router.get("/favorites")
def favorites(db: Database, principal: Identity) -> list[Favorite]:
    return list_favorites(db, principal)


@router.get("/favorites/{favorite_id}")
def favorite_detail(favorite_id: str, db: Database, principal: Identity) -> Favorite:
    return serialize_favorite(db, principal, get_favorite(db, principal, favorite_id))


@router.post("/favorites")
def save(body: SaveFavoriteRequest, db: Database, principal: MutationIdentity) -> Favorite:
    return save_favorite(db, principal, body)


@router.post("/favorites/{favorite_id}/rename")
def rename(
    favorite_id: str, body: RenameFavoriteRequest, db: Database, principal: MutationIdentity
) -> Favorite:
    return rename_favorite(db, principal, favorite_id, body)


@router.post("/favorites/{favorite_id}/delete", status_code=204)
def delete(
    favorite_id: str, body: FavoriteRevisionRequest, db: Database, principal: MutationIdentity
) -> Response:
    delete_favorite(db, principal, favorite_id, body)
    return Response(status_code=204)


@router.post("/favorites/{favorite_id}/run")
def run(
    favorite_id: str,
    body: FavoriteRevisionRequest,
    request: Request,
    db: Database,
    principal: MutationIdentity,
) -> Answer:
    return run_favorite(db, principal, favorite_id, body, request.state.request_id)
