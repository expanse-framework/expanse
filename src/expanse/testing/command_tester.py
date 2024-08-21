from cleo.io.inputs.string_input import StringInput
from cleo.io.outputs.buffered_output import BufferedOutput

from expanse.core.application import Application
from expanse.core.console.kernel import Kernel


class TestingCommand:
    def __init__(
        self, app: Application, command: str, parameters: str | None = None
    ) -> None:
        self._app = app
        self._command = command
        self._output: BufferedOutput = BufferedOutput()
        self._return_code: int | None = None

    @property
    def output(self) -> BufferedOutput:
        return self._output

    def run(self, parameters: str | None = None) -> int:
        self._output.clear()

        full_command = self._command
        if parameters:
            full_command += " " + parameters

        self._return_code = self._app.container.make(Kernel).handle(
            StringInput(full_command), self._output
        )

        return self._return_code


class CommandTester:
    def __init__(self, app: Application) -> None:
        self._app = app

    def command(self, command: str, parameters: str | None = None) -> TestingCommand:
        return TestingCommand(self._app, command, parameters)