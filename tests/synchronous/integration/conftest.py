import pytest

from expanse.foundation.application import Application
from expanse.testing.testing_command import TestingCommand
from expanse.types.testing import TestingCommandHelper


@pytest.fixture()
def testing_command(app: Application) -> TestingCommandHelper:
    def _testing_command(command: str, parameters: str | None = None) -> TestingCommand:
        return TestingCommand(app, command, parameters)

    return _testing_command