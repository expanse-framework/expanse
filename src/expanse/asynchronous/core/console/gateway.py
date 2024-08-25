import re
import sys

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from cleo.io.inputs.input import Input
from cleo.io.inputs.string_input import StringInput
from cleo.io.io import IO
from cleo.io.outputs.buffered_output import BufferedOutput
from cleo.io.outputs.output import Output
from cleo.io.outputs.stream_output import StreamOutput

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.console.console import Console as ConsoleApplication
from expanse.asynchronous.contracts.debug.exception_handler import ExceptionHandler
from expanse.asynchronous.core.application import Application
from expanse.asynchronous.core.bootstrap.boot_providers import BootProviders
from expanse.asynchronous.core.bootstrap.bootstrapper import Bootstrapper
from expanse.asynchronous.core.bootstrap.load_configuration import LoadConfiguration
from expanse.asynchronous.core.bootstrap.load_environment_variables import (
    LoadEnvironmentVariables,
)
from expanse.asynchronous.core.bootstrap.register_providers import RegisterProviders
from expanse.common.support._utils import string_to_class


class Gateway:
    _bootstrappers: ClassVar[list[type[Bootstrapper]]] = [
        LoadEnvironmentVariables,
        LoadConfiguration,
        RegisterProviders,
        BootProviders,
    ]

    def __init__(self, app: Application) -> None:
        self._app = app
        self._console: ConsoleApplication | None = None
        self._commands: list[type[Command]] = []
        self._command_paths: list[Path] = []
        self._commands_loaded: bool = False

    @property
    def console(self) -> ConsoleApplication:
        if self._console is not None:
            return self._console

        self._console = ConsoleApplication(self._app)
        self._console.auto_exits(False)
        self._console.catch_exceptions(False)

        return self._console

    async def handle(self, input: Input, output: Output | None = None) -> int:
        try:
            await self.bootstrap()
        except Exception as e:
            io = IO(
                input,
                output or StreamOutput(sys.stdout),
                output or StreamOutput(sys.stderr),
            )

            from cleo.ui.exception_trace import ExceptionTrace

            trace = ExceptionTrace(e)
            trace.render(io)

            return 1

        if output is None:
            output = StreamOutput(sys.stdout)

        try:
            return await self.console.run(input, output, output)
        except Exception as e:
            handler = await self._app.container.make(ExceptionHandler)

            await handler.report(e)
            await handler.render_for_console(output, e)

            return 1

    async def bootstrap(self) -> None:
        if not self._app.has_been_bootstrapped():
            await self._app.bootstrap_with(self._bootstrappers)

        if not self._commands_loaded:
            await self._discover_commands()

            self._commands_loaded = True

    def add_commands(self, commands: list[type[Command]]) -> None:
        self._commands.extend(commands)

    def add_command_paths(self, commands: list[Path]) -> None:
        self._command_paths.extend(commands)

    def add_command(self, command: type[Command]) -> None:
        self._commands.append(command)

    async def call(
        self,
        command_name: str,
        parameters: str | None = None,
        output: Output | None = None,
    ) -> int:
        await self.bootstrap()

        input = StringInput(parameters or "")
        output = output or BufferedOutput()
        command: Command = self.console.find(command_name)

        return await command.run(IO(input, output, output))

    async def _discover_commands(self) -> None:
        for path in self._command_paths:
            await self._load_path(path)

        for command in self._commands:
            self.console.add(command())

    async def _load_path(self, path: Path) -> None:
        if path.is_dir():
            for filepath in path.rglob("*.py"):
                if filepath.name.startswith("_"):
                    continue

                (
                    command_name,
                    command_factory,
                ) = await self._create_command_factory_from_path(filepath)
                self.console.command_loader.register_factory(
                    command_name, command_factory
                )

    async def _create_command_factory_from_path(
        self, path: Path
    ) -> tuple[str, Callable[[], Command]]:
        path = path.resolve().relative_to(self._app.base_path.resolve())
        name = path.stem.removesuffix("_command")
        classname = re.sub(r"(_)+", " ", name).title().replace(" ", "")
        command_name = " ".join(name.split("_"))

        def factory() -> Command:
            components = [
                # Import path
                path.with_suffix("").as_posix().replace("/", "."),
                # Class name
                f"{classname}Command",
            ]
            class_full_name = ".".join(components)
            class_: type[Command] = string_to_class(class_full_name)

            return class_()

        return command_name, factory
