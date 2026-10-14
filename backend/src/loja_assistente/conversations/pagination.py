import base64
import hashlib
import hmac
import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, or_

from loja_assistente.auth.service import Principal
from loja_assistente.config import settings


def encode(principal: Principal, scope: str, created_at: datetime, item_id: str) -> str:
    payload = json.dumps(
        [principal.tenant_id, principal.user_id, scope, created_at.isoformat(), item_id]
    ).encode()
    signature = hmac.new(
        settings.session_secret.get_secret_value().encode(), payload, hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(signature + payload).decode()


def decode(principal: Principal, scope: str, cursor: str | None):
    if cursor is None:
        return None
    try:
        if len(cursor) > 2048:
            raise ValueError
        raw = base64.b64decode(cursor, altchars=b"-_", validate=True)
        expected = hmac.new(
            settings.session_secret.get_secret_value().encode(), raw[32:], hashlib.sha256
        ).digest()
        if not hmac.compare_digest(raw[:32], expected):
            raise ValueError
        tenant, user, operation, timestamp, item_id = json.loads(raw[32:])
        date = datetime.fromisoformat(timestamp)
        if (
            (tenant, user, operation) != (principal.tenant_id, principal.user_id, scope)
            or date.tzinfo is None
            or not isinstance(item_id, str)
        ):
            raise ValueError
        return date, item_id
    except (ValueError, TypeError, UnicodeDecodeError):
        raise HTTPException(
            409, "A página não corresponde ao acesso atual. Recarregue o histórico."
        ) from None


def older(model, after):
    if after is None:
        return True
    date, item_id = after
    return or_(model.created_at < date, and_(model.created_at == date, model.id < item_id))
