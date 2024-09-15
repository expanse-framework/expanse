from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.database.console.commands.db_rollback import (
    DbRollbackCommand,  # noqa: F401
)
from expanse.testing.command_tester import CommandTester


@pytest.fixture(autouse=True)
def migrate(command_tester: CommandTester, app: Application) -> None:
    app.config["paths"]["database"] = (
        Path(__file__).parent.joinpath("fixtures").relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    command.run()


def test_rollback(command_tester: CommandTester, app: Application) -> None:
    command = command_tester.command("db rollback")

    return_code = command.run()
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
"""

    assert command.output.fetch() == expected


def test_rollback_with_step(command_tester: CommandTester, app: Application) -> None:
    command = command_tester.command("db rollback")

    return_code = command.run("--step 2")
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
  - Rolling back migration 1234567890 (Auto Migration)
"""

    assert command.output.fetch() == expected
