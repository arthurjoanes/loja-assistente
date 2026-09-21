from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from loja_assistente.auth.service import Principal
from loja_assistente.conversations.service import get_conversation
from loja_assistente.models import Conversation, Organization, User


def test_conversation_lock_rejects_competing_request_and_releases_after_commit(
    test_engine: Engine,
) -> None:
    # Independent committed connections exercise PostgreSQL row locks, not mocks or one savepoint.
    identity = "lock-" + uuid4().hex
    with Session(test_engine) as setup:
        setup.add(Organization(id=identity, name="Isolated lock fixture"))
        setup.flush()
        setup.add(
            User(
                id=identity,
                tenant_id=identity,
                name="Lock fixture",
                email=identity + "@example.invalid",
                role="manager",
                password_hash="unused",
            )
        )
        setup.flush()
        setup.add(Conversation(id=identity, tenant_id=identity, user_id=identity))
        setup.commit()
    principal = Principal(
        user_id=identity,
        tenant_id=identity,
        name="Lock fixture",
        email=identity + "@example.invalid",
        role="manager",
    )
    try:
        with Session(test_engine) as first, Session(test_engine) as second:
            assert get_conversation(first, principal, identity, lock=True).id == identity
            with pytest.raises(HTTPException) as rejected:
                get_conversation(second, principal, identity, lock=True)
            assert rejected.value.status_code == 409
            first.commit()
            assert get_conversation(second, principal, identity, lock=True).id == identity
            second.commit()
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Conversation).where(Conversation.id == identity))
            cleanup.execute(delete(User).where(User.id == identity))
            cleanup.execute(delete(Organization).where(Organization.id == identity))
            cleanup.commit()
