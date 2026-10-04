"""Bound Argon2 work with reservations committed independently of failed logins."""

import hashlib
import hmac
import math
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from loja_assistente.config import settings
from loja_assistente.database import SessionLocal
from loja_assistente.models import LoginAdmission

ACCOUNT_LIMIT = 5
SOURCE_LIMIT = 30
WINDOW_SECONDS = 60


def key_for(value: str) -> str:
    return hmac.new(settings.session_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def lock_keys(session: Session, keys: list[str]) -> None:
    # Stable order avoids deadlocks when two sources share an account.
    for key in sorted(keys):
        session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int(key[:16], 16) - (1 << 63)},
        )


def admit_login(email: str, source: str) -> list[tuple[str, datetime]]:
    account = key_for("account\0" + email.strip().lower())
    address = key_for("source\0" + source)
    admitted: list[tuple[str, datetime]] = []
    rejected = False
    retry_after = WINDOW_SECONDS
    # A 401 or a rollback in the caller must retain its failed attempt.
    with SessionLocal.begin() as session:
        lock_keys(session, [account, address])
        now = session.scalar(select(func.clock_timestamp()))
        assert now is not None
        expired = (
            select(LoginAdmission.key)
            .where(LoginAdmission.window_start <= now - timedelta(seconds=WINDOW_SECONDS))
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        session.execute(delete(LoginAdmission).where(LoginAdmission.key.in_(expired)))
        for key, limit in ((account, ACCOUNT_LIMIT), (address, SOURCE_LIMIT)):
            row = session.get(LoginAdmission, key)
            if row is not None and row.window_start <= now - timedelta(seconds=WINDOW_SECONDS):
                # The bounded cleanup may have left this key behind; its own
                # allowance still starts a fresh window under the same locks.
                row.window_start = now
                row.attempts = 0
            if row is not None and row.attempts >= limit:
                rejected = True
                retry_after = max(
                    1,
                    math.ceil(
                        (row.window_start + timedelta(seconds=WINDOW_SECONDS) - now).total_seconds()
                    ),
                )
                break
        if not rejected:
            for key in (account, address):
                row = session.get(LoginAdmission, key)
                if row is None:
                    row = LoginAdmission(key=key, window_start=now, attempts=0)
                    session.add(row)
                row.attempts += 1
                admitted.append((key, row.window_start))
    if rejected:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de entrada. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(retry_after)},
        )
    return admitted


def release_success(session: Session, admitted: list[tuple[str, datetime]]) -> None:
    # Only a successful committed session releases its own reservation.
    lock_keys(session, [key for key, _ in admitted])
    for key, window in admitted:
        session.execute(
            update(LoginAdmission)
            .where(LoginAdmission.key == key, LoginAdmission.window_start == window)
            .values(attempts=func.greatest(0, LoginAdmission.attempts - 1))
        )
