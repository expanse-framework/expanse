from pathlib import Path

import pytest

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.foundation.console.kernel import Kernel
from expanse.asynchronous.types.testing import TestingCommandHelper


class FooCommand(Command):
    name = "foo"

    async def handle(self) -> int:
        self.info("Foo")

        return 0


@pytest.fixture(autouse=True)
async def setup_kernel(app: Application) -> Kernel:
    kernel = await app.make(Kernel)
    kernel.add_command(FooCommand)

    kernel = await app.make(Kernel)
    kernel.add_command_paths([Path(__file__).parent.joinpath("fixtures/commands")])
    await kernel.bootstrap()

    yield kernel


async def test_external_command_can_be_called(
    testing_command: TestingCommandHelper,
) -> None:
    command = testing_command("foo")

    assert await command.run() == 0
    assert command.output.fetch().strip() == "Foo"


async def test_commands_can_be_auto_discovered(
    testing_command: TestingCommandHelper, app: Application
) -> None:
    command = testing_command("foo bar")

    assert await command.run() == 0
    assert command.output.fetch().strip() == "Foo Bar"
