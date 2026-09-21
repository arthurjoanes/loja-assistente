"""Avoid bigint overflow when validating quantity times unit price.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("valid_item_discount", "order_items", type_="check")
    op.create_check_constraint(
        "valid_item_discount",
        "order_items",
        "discount_cents >= 0 AND discount_cents <= quantity::numeric * unit_price_cents",
    )


def downgrade() -> None:
    # PostgreSQL refuses this downgrade if existing amounts exceed the old bigint expression.
    # The transactional migration then rolls back; it never truncates financial data.
    op.drop_constraint("valid_item_discount", "order_items", type_="check")
    op.create_check_constraint(
        "valid_item_discount",
        "order_items",
        "discount_cents >= 0 AND discount_cents <= quantity * unit_price_cents",
    )
