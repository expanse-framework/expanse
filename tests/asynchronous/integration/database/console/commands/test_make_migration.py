from pathlib import Path

import pendulum

from alembic import util
from treat.mock import Mockery  # type: ignore[import-untyped]

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database.console.commands.make_migration import (
    MakeMigrationCommand,  # noqa: F401
)
from expanse.asynchronous.testing.command_tester import CommandTester
from expanse.common.database.migration.migrator import Migrator


async def test_make_migration(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("1234567890")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make migration")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert await command.run("'Foo Migration'") == 0

    expected = f"""
  - Creating directory {tmp_path}/migrations...
  - Creating directory {tmp_path}/migrations... Done

  - Creating directory {tmp_path}/migrations/versions...
  - Creating directory {tmp_path}/migrations/versions... Done

  - Generating {tmp_path}/migrations/script.py.mako...
  - Generating {tmp_path}/migrations/script.py.mako... Done

  - Generating {tmp_path}/migrations/env.py...
  - Generating {tmp_path}/migrations/env.py... Done

  - Generating {tmp_path}/migrations/alembic.ini...
  - Generating {tmp_path}/migrations/alembic.ini... Done

  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_foo_migration.py...
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_foo_migration.py... Done

"""

    assert command.output.fetch() == expected


async def test_make_migration_autogenerated(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    app.config["paths"]["database"] = tmp_path
    app.config["database"]["default"] = "test"

    migrator = await app.container.make(Migrator)
    migrator.config.template_dir = Path(__file__).parent.joinpath("fixtures/templates")

    mockery.mock(util).should_receive("rev_id").and_return("1234567890")
    mockery.mock(app).should_receive("path").with_("models").and_return(
        Path(__file__).parent.joinpath("fixtures/models")
    )

    command = command_tester.command("make migration")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        return_code = await command.run("'Auto Migration' --auto")

    assert return_code == 0

    expected = f"""
  - Creating directory {tmp_path}/migrations...
  - Creating directory {tmp_path}/migrations... Done

  - Creating directory {tmp_path}/migrations/versions...
  - Creating directory {tmp_path}/migrations/versions... Done

  - Generating {tmp_path}/migrations/script.py.mako...
  - Generating {tmp_path}/migrations/script.py.mako... Done

  - Generating {tmp_path}/migrations/env.py...
  - Generating {tmp_path}/migrations/env.py... Done

  - Generating {tmp_path}/migrations/alembic.ini...
  - Generating {tmp_path}/migrations/alembic.ini... Done

  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_auto_migration.py...
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_auto_migration.py... Done

"""

    assert command.output.fetch() == expected

    content = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_1234567890_auto_migration.py"
    ).read_text()

    assert (
        content
        == """\
\"""
Auto Migration

Revision ID: 1234567890
Revises: 
Create Date: 2024-09-05 12:34:56
\"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1234567890'
down_revision: str | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('first_name', sa.String(), nullable=True),
    sa.Column('last_name', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')
    # ### end Alembic commands ###
"""
    )