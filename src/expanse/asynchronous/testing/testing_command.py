from cleo.io.outputs.buffered_output import BufferedOutput

from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.foundation.console.kernel import Kernel


class TestingCommand:
    def __init__(
        self, app: Application, command: str, parameters: str | None = None
    ) -> None:
        self._app = app
        self._command = command
        self._parameters = parameters or ""
        self._output: BufferedOutput = BufferedOutput()
        self._return_code: int | None = None

    @property
    def output(self) -> BufferedOutput:
        return self._output

    async def run(self) -> int:
        self._output.clear()

        self._return_code = await (await self._app.make(Kernel)).call(
            self._command, self._parameters, self._output
        )

        return self._return_code