from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from expanse.core.http.middleware.middleware_stack import MiddlewareStack


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.console.commands.command import Command
    from expanse.core.application import Application


class ApplicationBuilder:
    def __init__(self, app: Application) -> None:
        self._app: Application = app

    def with_kernels(self) -> Self:
        from expanse.core.console.kernel import Kernel as ConsoleKernel

        self._app.singleton(ConsoleKernel)

        return self

    def with_commands(self, commands: list[type[Command] | Path] | None = None) -> Self:
        from expanse.core.console.kernel import Kernel as ConsoleKernel

        if not commands:
            commands = [self._app.path("console/commands")]

        def _register_commands(kernel: ConsoleKernel) -> None:
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

    def with_middleware(self, callback: Callable[[MiddlewareStack], None]) -> Self:
        from expanse.core.http.gateway import Gateway

        def configure_middleware(gateway: Gateway) -> None:
            stack = MiddlewareStack()

            callback(stack)

            gateway.set_middleware(stack.middleware)

        self._app.on_resolved(Gateway, configure_middleware)

        return self

    def create(self) -> Application:
        return self._app
