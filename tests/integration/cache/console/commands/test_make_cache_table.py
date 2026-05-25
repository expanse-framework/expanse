from pathlib import Path

import pendulum
import pytest

from alembic import util
from treat.mock import Mockery

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.mark.usefixtures("setup_databases")
def test_command_creates_a_new_migration_file_with_necessary_operations(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("1234567890")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make cache table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run() == 0

    output: str = command.output.fetch()

    expected = f"""
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_create_cache_table.py...
  - Generating {tmp_path}/migrations/versions/2024_09_05_123456_1234567890_create_cache_table.py... Done
"""

    assert expected in output

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_1234567890_create_cache_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create cache table" in content
    assert "op.create_table('cache'" in content
    assert "sa.Column('key'" in content
    assert "sa.Column('data', sa.LargeBinary(), nullable=False)" in content
    assert (
        "sa.Column('expiration', sa.Integer().with_variant(mysql.INTEGER(unsigned=True), 'mysql'), nullable=True)"
        in content
    )
    assert "op.create_index(op.f('ix_cache_expiration')" in content
    assert "op.drop_table('cache')" in content


@pytest.mark.usefixtures("setup_databases")
def test_command_creates_a_new_migration_for_custom_table_name(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("0987654321")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make cache table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run("--table-name my_cache") == 0

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_0987654321_create_my_cache_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create my_cache table" in content
    assert "op.create_table('my_cache'" in content
    assert "op.create_index(op.f('ix_my_cache_expiration')" in content
    assert "op.drop_table('my_cache')" in content


@pytest.mark.usefixtures("setup_databases")
def test_command_creates_migration_with_locks_table_using_default_name(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("1122334455")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make cache table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run("--with-locks-table") == 0

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_1122334455_create_cache_table_and_cache_locks_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create cache table and cache_locks table" in content
    assert "op.create_table('cache'" in content
    assert "op.create_table('cache_locks'" in content
    assert "sa.Column('owner'" in content
    assert "op.drop_table('cache')" in content
    assert "op.drop_table('cache_locks')" in content


@pytest.mark.usefixtures("setup_databases")
def test_command_creates_migration_with_locks_table_using_custom_name(
    command_tester: CommandTester, app: Application, tmp_path: Path, mockery: Mockery
) -> None:
    mockery.mock(util).should_receive("rev_id").and_return("5544332211")

    app.config["paths"]["database"] = tmp_path

    command = command_tester.command("make cache table")

    with pendulum.travel_to(pendulum.datetime(2024, 9, 5, 12, 34, 56), freeze=True):
        assert command.run("--with-locks-table=my_locks") == 0

    migration_file = tmp_path.joinpath(
        "migrations/versions/2024_09_05_123456_5544332211_create_cache_table_and_my_locks_table.py"
    )
    assert migration_file.exists()

    content = migration_file.read_text()

    assert "Create cache table and my_locks table" in content
    assert "op.create_table('cache'" in content
    assert "op.create_table('my_locks'" in content
    assert "sa.Column('owner'" in content
    assert "op.drop_table('cache')" in content
    assert "op.drop_table('my_locks')" in content
