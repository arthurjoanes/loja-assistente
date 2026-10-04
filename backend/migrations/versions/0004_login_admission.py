"""Persist login admission independently of password verification failures.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_admission",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="login_admission_nonnegative"),
    )
    op.create_index("ix_login_admission_window", "login_admission", ["window_start"])


def downgrade() -> None:
    op.drop_index("ix_login_admission_window", table_name="login_admission")
    op.drop_table("login_admission")
