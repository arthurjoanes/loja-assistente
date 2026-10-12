"""Add personal saved plans and persistent clarification state.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations", sa.Column("pending_clarification", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("clarification_revision", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "clarification_revision_nonnegative", "conversations", "clarification_revision >= 0"
    )
    op.create_unique_constraint("uq_answers_owner_id", "answers", ["tenant_id", "user_id", "id"])
    op.create_table(
        "favorites",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=False),
        sa.Column("schema_version", sa.BigInteger(), nullable=False),
        sa.Column("source_answer_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id", "source_answer_id"],
            ["answers.tenant_id", "answers.user_id", "answers.id"],
            name="fk_favorites_source_owner",
        ),
        sa.UniqueConstraint(
            "tenant_id", "user_id", "source_answer_id", name="uq_favorites_owner_source"
        ),
        sa.CheckConstraint("revision >= 1", name="favorite_revision_positive"),
        sa.CheckConstraint("schema_version >= 1", name="favorite_schema_positive"),
    )
    op.create_index("ix_favorites_owner", "favorites", ["tenant_id", "user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_favorites_owner", table_name="favorites")
    op.drop_table("favorites")
    op.drop_constraint("uq_answers_owner_id", "answers", type_="unique")
    op.drop_constraint("clarification_revision_nonnegative", "conversations", type_="check")
    op.drop_column("conversations", "clarification_revision")
    op.drop_column("conversations", "pending_clarification")
