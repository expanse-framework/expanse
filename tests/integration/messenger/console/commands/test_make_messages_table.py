from pathlib import Path

import pendulum
import pytest

from alembic import util
from treat.mock import Mockery

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


def test_command_creates_a_new_migration_file_with_necessary_operations(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("1234567890")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make messages table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run() == 0

    output: str = command.output.fetch()

    expected = f"""
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_create_messages_table.py...
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_create_messages_table.py... Done
"""

    assert expected in output

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_1234567890_create_messages_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create messages table" in content
    assert "op.create_table('messages'" in content
    assert "sa.Column('id'" in content
    assert "sa.Column('body', sa.Text(), nullable=False)" in content
    assert "sa.Column('headers', sa.Text(), nullable=False)" in content
    assert "sa.Column('queue_name', sa.String(length=255), nullable=False)" in content
    assert (
        "sa.Column('created_at', sa.DateTime(timezone=True).with_variant(mysql.DATETIME(timezone=True, fsp=6), 'mysql'), nullable=False)"
        in content
    )
    assert (
        "sa.Column('available_at', sa.DateTime(timezone=True).with_variant(mysql.DATETIME(timezone=True, fsp=6), 'mysql'), nullable=False)"
        in content
    )
    assert (
        "sa.Column('delivered_at', sa.DateTime(timezone=True).with_variant(mysql.DATETIME(timezone=True, fsp=6), 'mysql'), nullable=True)"
        in content
    )
    assert "op.create_index(op.f('ix_messages_queue_name')" in content
    assert "op.create_index(op.f('ix_messages_available_at')" in content
    assert "op.create_index(op.f('ix_messages_delivered_at')" in content
    assert "op.drop_table('messages')" in content


def test_command_creates_a_new_migration_for_custom_table_name(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("0987654321")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make messages table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run("--table-name outbox") == 0

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_0987654321_create_outbox_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create outbox table" in content
    assert "op.create_table('outbox'" in content
    assert "op.create_index(op.f('ix_outbox_queue_name')" in content
    assert "op.drop_table('outbox')" in content
