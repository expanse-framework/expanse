from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self


if TYPE_CHECKING:
    from expanse.asynchronous.console.commands.command import Command
    from expanse.asynchronous.foundation.application import Application


class ApplicationBuilder:
    def __init__(self, app: Application) -> None:
        self._app: Application = app

    def with_kernels(self) -> Self:
        from expanse.asynchronous.foundation.console.kernel import (
            Kernel as ConsoleKernel,
        )

        self._app.singleton(ConsoleKernel)

        return self

    def with_commands(self, commands: list[type[Command] | Path] | None = None) -> Self:
        from expanse.asynchronous.foundation.console.kernel import (
            Kernel as ConsoleKernel,
        )

        if not commands:
            commands = [self._app.path("console/commands")]

        async def _register_commands(kernel: ConsoleKernel) -> None:
            command_paths: list[Path] = []
            command_classes: list[type[Command]] = []
            for command in commands:
                if isinstance(command, Path):
                    command_paths.append(command)
                    continue

                command_classes.append(command)

            kernel.add_command_paths(command_paths)
            kernel.add_commands(command_classes)

        self._app.after_resolving(ConsoleKernel, _register_commands)

        return self

    def create(self) -> Application:
        return self._app
