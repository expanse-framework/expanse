"""
Create cache locks table

Revision ID: d5b2c3e4f567
Revises: c4a1b2d3e456
Create Date: 2026-05-16 00:00:01
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d5b2c3e4f567"
down_revision: str | None = "c4a1b2d3e456"


def upgrade() -> None:
    op.create_table(
        "cache_locks",
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("expiration", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("cache_locks", if_exists=True)
