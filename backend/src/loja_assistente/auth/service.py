import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from loja_assistente.config import settings
from loja_assistente.database import get_db
from loja_assistente.models import LoginSession, Store, StorePermission, User

password_hasher = PasswordHasher()
SESSION_COOKIE = "la_session"


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    name: str
    email: str
    role: str


class InvalidStoreAccess(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=403, detail="Escopo de loja não autorizado.")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def session_digest(token: str) -> str:
    return hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def require_origin(request: Request) -> None:
    if request.headers.get("origin") not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origem da requisição não autorizada.")


def current_session(request: Request, db: Session) -> LoginSession:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    session = db.get(LoginSession, session_digest(token))
    if session is None or session.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    return session


def get_principal(request: Request, db: Annotated[Session, Depends(get_db)]) -> Principal:
    session = current_session(request, db)
    user = db.scalar(
        select(User).where(User.id == session.user_id, User.tenant_id == session.tenant_id)
    )
    if user is None or (user.email.endswith("@demo.local") and not settings.demo_mode):
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    return Principal(user.id, user.tenant_id, user.name, user.email, user.role)


def require_csrf(
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    require_origin(request)
    session = current_session(request, db)
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied or not secrets.compare_digest(supplied, session.csrf_token):
        raise HTTPException(status_code=403, detail="Token CSRF inválido. Recarregue a página.")
    return principal


def permitted_stores(db: Session, principal: Principal) -> list[Store]:
    return list(
        db.scalars(
            select(Store)
            .join(
                StorePermission,
                and_(
                    StorePermission.tenant_id == Store.tenant_id,
                    StorePermission.store_id == Store.id,
                ),
            )
            .where(
                Store.tenant_id == principal.tenant_id,
                StorePermission.tenant_id == principal.tenant_id,
                StorePermission.user_id == principal.user_id,
            )
            .order_by(Store.id)
        )
    )


def assert_store_access(db: Session, principal: Principal, ids: list[str]) -> list[Store]:
    stores = permitted_stores(db, principal)
    allowed = {store.id: store for store in stores}
    if not ids or not set(ids).issubset(allowed):
        raise InvalidStoreAccess()
    return [allowed[store_id] for store_id in sorted(set(ids))]


def resolve_store_references(
    db: Session, principal: Principal, references: list[str]
) -> list[Store]:
    stores = permitted_stores(db, principal)
    if not references:
        if not stores:
            raise InvalidStoreAccess()
        return stores
    resolved: list[str] = []
    for reference in references:
        normalized = reference.strip().casefold()
        matches = [
            store for store in stores if normalized in (store.id.casefold(), store.name.casefold())
        ]
        if len(matches) != 1:
            raise InvalidStoreAccess()
        resolved.append(matches[0].id)
    return assert_store_access(db, principal, resolved)
