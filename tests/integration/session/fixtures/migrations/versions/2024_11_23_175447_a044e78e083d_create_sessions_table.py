"""
Create sessions table

Revision ID: a044e78e083d
Revises: 2781cf44099d
Create Date: 2024-11-23 17:54:47.238456
"""

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a044e78e083d"
down_revision: str | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            sa.String(40),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_sessions_last_activity",
            "sessions",
            ["last_activity"],
            unique=False,
            if_not_exists=op.get_context().dialect.name != "mysql",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("sessions", if_exists=True)
