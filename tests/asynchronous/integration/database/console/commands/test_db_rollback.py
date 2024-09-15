from pathlib import Path

import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.database.console.commands.db_rollback import (
    DbRollbackCommand,  # noqa: F401
)
from expanse.asynchronous.testing.command_tester import CommandTester


@pytest.fixture(autouse=True)
async def migrate(command_tester: CommandTester, app: Application) -> None:
    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    await command.run()


async def test_rollback(command_tester: CommandTester, app: Application) -> None:
    command = command_tester.command("db rollback")

    return_code = await command.run()
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
"""

    assert command.output.fetch() == expected


async def test_rollback_with_step(
    command_tester: CommandTester, app: Application
) -> None:
    command = command_tester.command("db rollback")

    return_code = await command.run("--step 2")
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
  - Rolling back migration 1234567890 (Auto Migration)
"""

    assert command.output.fetch() == expected
