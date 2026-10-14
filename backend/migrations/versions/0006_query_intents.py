"""Persist request admission before interpreting a query.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_intents",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("client_request_id", sa.String(64), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("answer_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id", "answer_id"],
            ["answers.tenant_id", "answers.user_id", "answers.id"],
        ),
    )


def downgrade() -> None:
    op.drop_table("query_intents")
