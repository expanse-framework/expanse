from cleo.io.inputs.string_input import StringInput
from cleo.io.outputs.buffered_output import BufferedOutput

from expanse.asynchronous.contracts.debug.exception_handler import ExceptionHandler
from expanse.asynchronous.core.application import Application
from expanse.asynchronous.core.console.gateway import Gateway


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

    async def run(self, parameters: str | None = None) -> int:
        self._output.clear()

        full_command = self._command
        if parameters:
            full_command += " " + parameters

        kernel = await self._app.container.make(Gateway)
        handler = await self._app.container.make(ExceptionHandler)
        with handler.raise_unhandled_exceptions():
            self._return_code = await kernel.handle(
                StringInput(full_command), self._output
            )

        return self._return_code


class CommandTester:
    def __init__(self, app: Application) -> None:
        self._app = app

    def command(self, command: str, parameters: str | None = None) -> TestingCommand:
        return TestingCommand(self._app, command, parameters)
