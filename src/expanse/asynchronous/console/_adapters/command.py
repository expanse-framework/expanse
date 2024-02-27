from __future__ import annotations

from typing import TYPE_CHECKING

from cleo.commands.command import Command as BaseCommand
from cleo.exceptions import CleoError
from cleo.io.inputs.string_input import StringInput
from cleo.io.null_io import NullIO


if TYPE_CHECKING:
    from cleo.io.io import IO

    from expanse.asynchronous.console._adapters.application import Application


class Command(BaseCommand):
    application: Application

    async def execute(self, io: IO) -> int:
        self._io = io

        try:
            return await self.handle()
        except KeyboardInterrupt:
            return 1

    async def handle(self, *args, **kwargs) -> int:
        """
        Executes the command.
        """
        raise NotImplementedError()

    async def run(self, io: IO) -> int:
        self.merge_application_definition()

        try:
            io.input.bind(self.definition)
        except CleoError:
            if not self._ignore_validation_errors:
                raise

        self.initialize(io)

        if io.is_interactive():
            self.interact(io)

        if io.input.has_argument("command") and io.input.argument("command") is None:
            io.input.set_argument("command", self.name)

        io.input.validate()

        status_code = await self.execute(io)

        if status_code is None:
            status_code = 0

        return status_code

    async def call(self, name: str, args: str | None = None) -> int:
        """
        Call another command.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self.application is not None
        command = self.application.get(name)

        return await self.application._run_command(command, self._io.with_input(input))

    async def call_silent(self, name: str, args: str | None = None) -> int:
        """
        Call another command silently.
        """
        if args is None:
            args = ""

        input = StringInput(args)
        assert self.application is not None
        command = self.application.get(name)

        return self.application._run_command(command, NullIO(input))
