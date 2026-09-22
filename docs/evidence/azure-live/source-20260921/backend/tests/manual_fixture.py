"""Pequeno oráculo independente: valores esperados estão em docs/manual-fixture.md."""

from datetime import date, datetime, timedelta
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from loja_assistente.auth.service import hash_password
from loja_assistente.models import (
    Coverage,
    Dataset,
    Order,
    OrderItem,
    Organization,
    Product,
    Store,
    StorePermission,
    User,
)

PASSWORD = "LojaDemo!2026"
IDENTITIES = {
    "manager_a": "gerente.a@demo.local",
    "supervisor_a": "supervisor.a@demo.local",
    "manager_b": "gerente.b@demo.local",
}
ORIGIN = "http://localhost:3102"


@lru_cache(maxsize=1)
def fixture_password_hash() -> str:
    return hash_password(PASSWORD)


def seed_manual(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)) is not None:
        raise RuntimeError("A fixture manual exige banco de testes vazio.")
    db.add_all(
        [
            Organization(id="org_a", name="Aurora Comércio"),
            Organization(id="org_b", name="Brisa Comércio"),
        ]
    )
    db.flush()
    db.add_all(
        [
            Store(tenant_id="org_a", id="a001", external_id="STORE-001", name="Centro"),
            Store(tenant_id="org_a", id="a002", external_id="STORE-002", name="Jardins"),
            Store(tenant_id="org_b", id="b001", external_id="STORE-001", name="Centro"),
            Product(tenant_id="org_a", id="pa01", external_id="PROD-001", name="Caneca"),
            Product(tenant_id="org_a", id="pa02", external_id="PROD-002", name="Garrafa"),
            Product(tenant_id="org_a", id="pa03", external_id="PROD-003", name="Ecobag"),
            Product(tenant_id="org_b", id="pb01", external_id="PROD-001", name="Caneca"),
        ]
    )
    for user_id, email in IDENTITIES.items():
        db.add(
            User(
                id=user_id,
                tenant_id="org_b" if user_id == "manager_b" else "org_a",
                name=user_id,
                email=email,
                role="supervisor" if user_id == "supervisor_a" else "manager",
                password_hash=fixture_password_hash(),
            )
        )
    db.flush()
    for tenant_id, user_id, store_id in [
        ("org_a", "manager_a", "a001"),
        ("org_a", "supervisor_a", "a001"),
        ("org_a", "supervisor_a", "a002"),
        ("org_b", "manager_b", "b001"),
    ]:
        db.add(StorePermission(tenant_id=tenant_id, user_id=user_id, store_id=store_id))
    for tenant_id, store_id in [("org_a", "a001"), ("org_a", "a002"), ("org_b", "b001")]:
        for offset in range(7):
            db.add(
                Coverage(
                    tenant_id=tenant_id,
                    store_id=store_id,
                    date=date(2026, 8, 10) + timedelta(days=offset),
                )
            )
    orders = [
        (
            "org_a",
            "oa1",
            "a001",
            "2026-08-15T02:59:59+00:00",
            "completed",
            [("pa01", 2, 1000, 100), ("pa02", 1, 600, 0)],
        ),
        (
            "org_a",
            "oa2",
            "a001",
            "2026-08-15T03:00:00+00:00",
            "completed",
            [("pa01", 1, 1000, 0), ("pa03", 3, 200, 0)],
        ),
        (
            "org_a",
            "oa3",
            "a001",
            "2026-08-16T15:00:00+00:00",
            "completed",
            [("pa02", 2, 600, 200), ("pa03", 5, 200, 0)],
        ),
        ("org_a", "oa4", "a001", "2026-08-16T16:00:00+00:00", "completed", [("pa01", 1, 1000, 0)]),
        ("org_a", "oa5", "a001", "2026-08-16T17:00:00+00:00", "cancelled", [("pa01", 10, 1000, 0)]),
        (
            "org_a",
            "oa6",
            "a002",
            "2026-08-16T18:00:00+00:00",
            "completed",
            [("pa01", 1, 1000, 0), ("pa02", 1, 600, 0)],
        ),
        (
            "org_b",
            "ob1",
            "b001",
            "2026-08-16T19:00:00+00:00",
            "completed",
            [("pb01", 2, 1700, 100)],
        ),
    ]
    for tenant_id, order_id, store_id, instant, status, items in orders:
        db.add(
            Order(
                tenant_id=tenant_id,
                id=order_id,
                store_id=store_id,
                external_id="ORDER-001" if order_id == "ob1" else f"ORDER-{order_id[2:].zfill(3)}",
                occurred_at=datetime.fromisoformat(instant),
                status=status,
            )
        )
        db.flush()
        for index, (product_id, quantity, price, discount) in enumerate(items):
            db.add(
                OrderItem(
                    tenant_id=tenant_id,
                    id=f"{order_id}-item-{index}",
                    order_id=order_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price_cents=price,
                    discount_cents=discount,
                )
            )
    db.add(
        Dataset(
            version="manual-v1",
            seed=0,
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 17),
            manifest={"fixture": "manual-v1", "orders": 7, "items": 11, "coverage_rows": 21},
        )
    )
    db.flush()
