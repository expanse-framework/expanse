import pytest

from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.testing.testing_command import TestingCommand
from expanse.asynchronous.types.testing import TestingCommandHelper


@pytest.fixture()
def testing_command(app: Application) -> TestingCommandHelper:
    def _testing_command(command: str, parameters: str | None = None) -> TestingCommand:
        return TestingCommand(app, command, parameters)

    return _testing_command
