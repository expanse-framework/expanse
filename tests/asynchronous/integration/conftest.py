import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.testing.command_tester import CommandTester


@pytest.fixture()
def command_tester(app: Application) -> CommandTester:
    return CommandTester(app)
