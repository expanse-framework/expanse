from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
async def migrate(command_tester: CommandTester, app: Application) -> None:
    app.config["paths"]["database"] = (
        Path(__file__)
        .parent.parent.parent.joinpath("fixtures")
        .relative_to(app.base_path)
    )
    app.config["database"]["default"] = "test"

    command = command_tester.command("db migrate")

    command.run()


async def test_rollback(command_tester: CommandTester, app: Application) -> None:
    command = command_tester.command("db rollback")

    return_code = command.run()
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
"""

    assert command.output.fetch() == expected


async def test_rollback_with_step(
    command_tester: CommandTester, app: Application
) -> None:
    command = command_tester.command("db rollback")

    return_code = command.run("--step 2")
    assert return_code == 0

    expected = """
  - Rolling back migration 1234567891 (Foo Migration)
  - Rolling back migration 1234567890 (Auto Migration)
"""

    assert command.output.fetch() == expected
