from datetime import UTC, datetime
from datetime import date as calendar_date
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from loja_assistente.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class Store(Base):
    __tablename__ = "stores"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("tenant_id", "external_id"),)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("tenant_id", "id"),)


class StorePermission(Base):
    __tablename__ = "store_permissions"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        ForeignKeyConstraint(["tenant_id", "store_id"], ["stores.tenant_id", "stores.id"]),
    )


class Product(Base):
    __tablename__ = "products"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    __table_args__ = (UniqueConstraint("tenant_id", "external_id"),)


class Order(Base):
    __tablename__ = "orders"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "store_id"], ["stores.tenant_id", "stores.id"]),
        UniqueConstraint("tenant_id", "external_id"),
        CheckConstraint("status IN ('completed', 'cancelled')", name="valid_order_status"),
        Index("ix_orders_scope_time", "tenant_id", "store_id", "occurred_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64))
    product_id: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int]
    unit_price_cents: Mapped[int] = mapped_column(BigInteger)
    discount_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "order_id"], ["orders.tenant_id", "orders.id"]),
        ForeignKeyConstraint(["tenant_id", "product_id"], ["products.tenant_id", "products.id"]),
        CheckConstraint("quantity > 0 AND unit_price_cents >= 0", name="positive_item_amounts"),
        CheckConstraint(
            "discount_cents >= 0 AND discount_cents <= quantity::numeric * unit_price_cents",
            name="valid_item_discount",
        ),
        Index("ix_order_items_order", "tenant_id", "order_id"),
    )


class Coverage(Base):
    __tablename__ = "coverage"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    store_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[calendar_date] = mapped_column(primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "store_id"], ["stores.tenant_id", "stores.id"]),
    )


class Dataset(Base):
    __tablename__ = "datasets"
    version: Mapped[str] = mapped_column(String(80), primary_key=True)
    seed: Mapped[int]
    start_date: Mapped[calendar_date]
    end_date: Mapped[calendar_date]
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(160), default="Nova conversa")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        UniqueConstraint("tenant_id", "user_id", "id"),
        Index("ix_conversations_owner", "tenant_id", "user_id", "created_at"),
    )


class AnswerRecord(Base):
    __tablename__ = "answers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    conversation_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "user_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.user_id", "conversations.id"],
        ),
        Index("ix_answers_conversation", "tenant_id", "user_id", "conversation_id"),
    )


class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16))
    capability: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    interpretation_ms: Mapped[int]
    query_ms: Mapped[int]
    response_ms: Mapped[int]
    interpreter_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        Index("ix_operations_owner", "tenant_id", "user_id", "created_at"),
    )
