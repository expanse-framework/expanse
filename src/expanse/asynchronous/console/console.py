from __future__ import annotations

import os
import sys

from typing import TYPE_CHECKING
from typing import cast

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.console.commands.help import HelpCommand
from expanse.asynchronous.console.commands.list import ListCommand
from expanse.common.console.console import Console as BaseConsole


if TYPE_CHECKING:
    from cleo.io.inputs.input import Input
    from cleo.io.io import IO
    from cleo.io.outputs.output import Output

    from expanse.asynchronous.core.application import Application


class Console(BaseConsole[Command]):
    def __init__(self, app: Application) -> None:
        super().__init__()

        self._app = app

    async def run(
        self,
        input: Input | None = None,
        output: Output | None = None,
        error_output: Output | None = None,
    ) -> int:
        try:
            io = self.create_io(input, output, error_output)

            self._configure_io(io)

            try:
                exit_code = await self._run(io)
            except BrokenPipeError:
                # If we are piped to another process, it may close early and send a
                # SIGPIPE: https://docs.python.org/3/library/signal.html#note-on-sigpipe
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, sys.stdout.fileno())
                exit_code = 0
            except Exception as e:
                if not self._catch_exceptions:
                    raise

                self.render_error(e, io)

                exit_code = 1
                # TODO: Custom error exit codes
        except KeyboardInterrupt:
            exit_code = 1

        if self._auto_exit:
            sys.exit(exit_code)

        return exit_code

    @property
    def default_commands(self) -> list[Command]:
        return [HelpCommand(), ListCommand()]

    def get_help_command(self, command: Command) -> Command:
        help_command: HelpCommand = cast(HelpCommand, self.get("help"))
        help_command.set_command(command)

        return help_command

    async def _run(self, io: IO) -> int:
        if io.input.has_parameter_option(["--version", "-V"], True):
            io.write_line(self.long_version)

            return 0

        self._setup_command(io)

        assert self._running_command is not None

        exit_code = await self._run_command(self._running_command, io)
        self._running_command = None

        return exit_code

    async def _run_command(self, command: Command, io: IO) -> int:
        command.set_application(self._app)

        return await command.run(io)
