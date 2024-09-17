from io import StringIO
from typing import Self

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
        self._user_input: str | None = None

    @property
    def output(self) -> BufferedOutput:
        return self._output

    def with_user_input(self, user_input: str) -> Self:
        self._user_input = user_input

        return self

    async def run(self, parameters: str | None = None) -> int:
        self._output.clear()

        full_command = self._command
        if parameters:
            full_command += " " + parameters

        gateway = await self._app.container.get(Gateway)
        handler = await self._app.container.get(ExceptionHandler)

        input = StringInput(full_command)
        input.set_stream(StringIO())
        if self._user_input:
            input.stream.truncate(0)
            input.stream.seek(0)
            input.stream.write(self._user_input)
            input.stream.seek(0)
            input.interactive()

        with handler.raise_unhandled_exceptions():
            self._return_code = await gateway.handle(input, self._output)

        return self._return_code


class CommandTester:
    def __init__(self, app: Application) -> None:
        self._app = app

    def command(self, command: str, parameters: str | None = None) -> TestingCommand:
        return TestingCommand(self._app, command, parameters)
