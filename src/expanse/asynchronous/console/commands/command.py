from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import TypeVar

from cleo.exceptions import CleoError
from cleo.io.inputs.string_input import StringInput
from cleo.io.null_io import NullIO

from expanse.common.console.command import Command as BaseCommand


if TYPE_CHECKING:
    from cleo.io.io import IO

    from expanse.asynchronous.console.console import Console  # noqa: TID
    from expanse.asynchronous.core.application import Application

TApplication = TypeVar("TApplication", bound="Console")


class Command(BaseCommand[TApplication], ABC):
    def __init__(self) -> None:
        super().__init__()

        self._application: Application | None = None

    @abstractmethod
    async def handle(self, *args, **kwargs) -> int | None: ...

    async def run(self, io: IO) -> int:
        self.merge_console_definition()

        try:
            io.input.bind(self.definition)
        except CleoError:
            if not self._ignore_validation_errors:
                raise

        if io.input.has_argument("command") and io.input.argument("command") is None:
            io.input.set_argument("command", self.name)

        io.input.validate()

        status_code = await self.execute(io)

        if status_code is None:
            status_code = 0

        return status_code

    async def execute(self, io: IO) -> int | None:
        self._io = io

        try:
            if not self._application:
                return await self.handle()

            return await self._application.container.call(self.handle)
        except KeyboardInterrupt:
            return 1

    def set_application(self, application: Application) -> None:
        self._application = application

    async def call(self, name: str, args: str | None = None) -> int:
        """
        Call another command.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self._console is not None
        command = self._console.get(name)

        return await self._console._run_command(command, self._io.with_input(input))

    async def call_silent(self, name: str, args: str | None = None) -> int:
        """
        Call another command silently.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self._console is not None
        command = self._console.get(name)

        return await self._console._run_command(command, NullIO(input))
