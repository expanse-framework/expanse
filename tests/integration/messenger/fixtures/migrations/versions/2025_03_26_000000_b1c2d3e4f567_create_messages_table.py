"""
Create messages table

Revision ID: b1c2d3e4f567
Revises:
Create Date: 2025-03-26 00:00:00
"""

import sqlalchemy as sa

from alembic import op
from sqlalchemy.dialects.mysql import DATETIME


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f567"
down_revision: str | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.INTEGER(), "sqlite"),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("headers", sa.Text(), nullable=False),
        sa.Column("queue_name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True).with_variant(
                DATETIME(timezone=True, fsp=6), "mysql"
            ),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True).with_variant(
                DATETIME(timezone=True, fsp=6), "mysql"
            ),
            nullable=False,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True).with_variant(
                DATETIME(timezone=True, fsp=6), "mysql"
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_messages_queue_name",
            "messages",
            ["queue_name"],
            unique=False,
            if_not_exists=op.get_context().dialect.name != "mysql",
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_messages_available_at",
            "messages",
            ["available_at"],
            unique=False,
            if_not_exists=op.get_context().dialect.name != "mysql",
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_messages_delivered_at",
            "messages",
            ["delivered_at"],
            unique=False,
            if_not_exists=op.get_context().dialect.name != "mysql",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("messages", if_exists=True)
