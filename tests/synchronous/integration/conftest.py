import pytest

from expanse.core.application import Application
from expanse.testing.command_tester import CommandTester


@pytest.fixture()
def command_tester(app: Application) -> CommandTester:
    return CommandTester(app)
