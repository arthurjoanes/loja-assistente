from datetime import UTC, datetime

from sqlalchemy import select

from loja_assistente.models import AnswerRecord, Conversation, StorePermission


def test_conversation_pages_keep_timestamp_ties_and_owner_scope(manager_client, db):
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(51):
        db.add(
            Conversation(
                id=f"page-{index:03}",
                tenant_id="org_a",
                user_id="manager_a",
                title=f"Conversation {index}",
                created_at=instant,
            )
        )
    db.add(
        Conversation(
            id="private",
            tenant_id="org_b",
            user_id="manager_b",
            title="Private",
            created_at=instant,
        )
    )
    db.commit()
    first = manager_client.get("/api/conversations/page").json()
    second = manager_client.get(
        "/api/conversations/page", params={"cursor": first["next_cursor"]}
    ).json()
    ids = [row["id"] for row in first["items"] + second["items"]]
    assert ids == [f"page-{index:03}" for index in range(50, -1, -1)]
    assert first["has_more"] and not second["has_more"]
    assert (
        manager_client.get(
            "/api/conversations/page", params={"cursor": first["next_cursor"] + "bad"}
        ).status_code
        == 409
    )


def test_messages_paginate_101_answers_and_revoked_grants_block_cursor(manager_client, db):
    initial = manager_client.post(
        "/api/assistant/query", json={"question": "Quanto vendi ontem?"}
    ).json()
    original = db.get(AnswerRecord, initial["id"])
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    original.created_at = instant
    for index in range(100):
        key = f"answer-{index:03}"
        db.add(
            AnswerRecord(
                id=key,
                tenant_id="org_a",
                user_id="manager_a",
                conversation_id=initial["conversation_id"],
                payload=initial | {"id": key},
                created_at=instant,
            )
        )
    db.commit()
    detail = manager_client.get("/api/conversations/" + initial["conversation_id"]).json()
    cursor = detail["messages_next_cursor"]
    older = manager_client.get(
        f"/api/conversations/{initial['conversation_id']}/messages", params={"cursor": cursor}
    ).json()
    ids = [row["id"] for row in detail["messages"] + older["items"]]
    assert len(ids) == len(set(ids)) == 101
    assert older["next_cursor"] is None
    permission = db.scalar(
        select(StorePermission).where(
            StorePermission.tenant_id == "org_a", StorePermission.user_id == "manager_a"
        )
    )
    assert permission is not None
    db.delete(permission)
    db.commit()
    assert (
        manager_client.get(
            f"/api/conversations/{initial['conversation_id']}/messages", params={"cursor": cursor}
        ).status_code
        == 403
    )
    assert manager_client.get("/api/conversations/page").json()["items"] == []
