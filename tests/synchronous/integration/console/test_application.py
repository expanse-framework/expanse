from pathlib import Path

import pytest

from expanse.console.commands.command import Command
from expanse.core.application import Application
from expanse.core.console.gateway import Gateway
from expanse.testing.command_tester import CommandTester


class FooCommand(Command):
    name = "foo"

    def handle(self) -> int:
        self.info("Foo")

        return 0


@pytest.fixture(autouse=True)
def setup_kernel(app: Application) -> Gateway:
    kernel = app.container.make(Gateway)
    kernel.add_command(FooCommand)
    kernel.add_command_paths([Path(__file__).parent.joinpath("fixtures/commands")])
    kernel.bootstrap()

    return kernel


def test_external_command_can_be_called(command_tester: CommandTester, app) -> None:
    command = command_tester.command("foo")

    assert command.run() == 0
    assert command.output.fetch().strip() == "Foo"


def test_commands_can_be_auto_discovered(command_tester: CommandTester) -> None:
    command = command_tester.command("foo bar")

    assert command.run() == 0
    assert command.output.fetch().strip() == "Foo Bar"
