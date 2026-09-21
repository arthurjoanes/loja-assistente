import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.auth.service import (
    SESSION_COOKIE,
    Principal,
    current_session,
    get_principal,
    hash_password,
    permitted_stores,
    require_csrf,
    require_origin,
    session_digest,
    verify_password,
)
from loja_assistente.config import settings
from loja_assistente.database import get_db
from loja_assistente.models import LoginSession, Organization, User

router = APIRouter(prefix="/auth", tags=["Autenticação"])
# Work for unknown identities is comparable to a regular password verification.
_dummy_hash = hash_password(secrets.token_urlsafe(24))


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


def profile(db: Session, principal: Principal, csrf_token: str) -> dict[str, Any]:
    organization = db.get(Organization, principal.tenant_id)
    if organization is None:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return {
        "user": {
            "id": principal.user_id,
            "name": principal.name,
            "email": principal.email,
            "role": principal.role,
            "organization": {"id": organization.id, "name": organization.name},
            "stores": [
                {"id": store.id, "name": store.name} for store in permitted_stores(db, principal)
            ],
        },
        "csrf_token": csrf_token,
        "reference_date": settings.reference_date.isoformat(),
        "dataset_version": settings.dataset_version,
        "llm_available": bool(settings.llm_enabled and settings.openai_api_key),
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    require_origin(request)
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    valid = verify_password(payload.password, user.password_hash if user else _dummy_hash)
    if user is None or not valid or (not settings.demo_mode and user.email.endswith("@demo.local")):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    old_token = request.cookies.get(SESSION_COOKIE)
    if old_token:
        old_session = db.get(LoginSession, session_digest(old_token))
        if old_session is not None:
            db.delete(old_session)
    raw_token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    session = LoginSession(
        id=session_digest(raw_token),
        tenant_id=user.tenant_id,
        user_id=user.id,
        csrf_token=csrf_token,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return profile(
        db, Principal(user.id, user.tenant_id, user.name, user.email, user.role), csrf_token
    )


@router.get("/me")
def me(
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return profile(db, principal, current_session(request, db).csrf_token)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    db.delete(current_session(request, db))
    db.commit()
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
    return {"ok": True}
