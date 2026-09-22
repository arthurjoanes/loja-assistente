"""Durable tenant provider allowance; no default authorization or daily reset.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_budget_accounts",
        sa.Column("tenant_id", sa.String(64), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("calls_limit", sa.BigInteger(), nullable=False),
        sa.Column("input_limit", sa.BigInteger(), nullable=False),
        sa.Column("output_limit", sa.BigInteger(), nullable=False),
        sa.Column("committed_calls", sa.BigInteger(), nullable=False),
        sa.Column("committed_input", sa.BigInteger(), nullable=False),
        sa.Column("committed_output", sa.BigInteger(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("blocked_reason", sa.String(160)),
        sa.Column("configured_reason", sa.String(500), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "calls_limit >= 0 AND input_limit >= 0 AND output_limit >= 0 AND "
            "committed_calls >= 0 AND committed_input >= 0 AND committed_output >= 0",
            name="provider_budget_nonnegative",
        ),
    )
    op.create_table(
        "provider_reservations",
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("provider_budget_accounts.tenant_id"),
            primary_key=True,
        ),
        sa.Column("call_id", sa.String(64), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("model_requested", sa.String(200), nullable=False),
        sa.Column("reserved_input", sa.BigInteger(), nullable=False),
        sa.Column("reserved_output", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("observation", postgresql.JSONB()),
        sa.Column("observation_source", sa.String(32)),
        sa.Column("evidence_reference", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "reserved_input > 0 AND reserved_output > 0", name="provider_reservation_positive"
        ),
        sa.CheckConstraint(
            "state IN ('reserved','dispatched','unknown','reconciled','canceled')",
            name="provider_reservation_state",
        ),
        sa.CheckConstraint(
            "(state IN ('reserved','canceled') AND dispatched_at IS NULL) OR "
            "(state IN ('dispatched','unknown','reconciled') AND dispatched_at IS NOT NULL)",
            name="provider_reservation_dispatch_state",
        ),
    )
    op.create_index(
        "ix_provider_reservations_request", "provider_reservations", ["tenant_id", "request_id"]
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM provider_reservations)")):
        raise RuntimeError(
            "Refusing to erase a provider usage ledger; preserve and review it explicitly."
        )
    op.drop_table("provider_reservations")
    op.drop_table("provider_budget_accounts")
