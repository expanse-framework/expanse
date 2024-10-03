"""
Foo Migration

Revision ID: 1234567891
Revises: 1234567890
Create Date: 2024-09-06 12:34:56
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1234567891"
down_revision: str | None = "1234567890"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "active", sa.Boolean(), nullable=False, default=True, server_default="true"
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "active")
