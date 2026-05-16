"""
Create cache table

Revision ID: c4a1b2d3e456
Revises:
Create Date: 2026-05-16 00:00:00
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4a1b2d3e456"
down_revision: str | None = None


def upgrade() -> None:
    op.create_table(
        "cache",
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("expiration", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("cache", if_exists=True)
