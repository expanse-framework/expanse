from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from expanse.container.container import Container
from expanse.core.http.middleware.middleware_stack import MiddlewareStack


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.console.commands.command import Command
    from expanse.core.application import Application
    from expanse.core.console.kernel import Kernel as ConsoleKernel
    from expanse.core.http.gateway import Gateway


class ApplicationBuilder:
    def __init__(self, base_path: Path) -> None:
        self._base_path: Path = base_path
        self._container = Container()
        self._register_commands_callback: Callable[[ConsoleKernel], None] | None = None
        self._configure_middleware_stack: Callable[[Gateway], None] | None = None
        self._configure_kernels: Callable[[Container], None] | None = None

    def with_kernels(self) -> Self:
        def configure_kernels(container: Container) -> None:
            from expanse.core.console.kernel import Kernel as ConsoleKernel

            container.singleton(ConsoleKernel)

        self._configure_kernels = configure_kernels

        return self

    def with_commands(self, commands: list[type[Command] | Path] | None = None) -> Self:
        def _register_commands(kernel: ConsoleKernel) -> None:
            nonlocal commands

            if not commands:
                commands = [kernel._app.path("console/commands")]

            command_paths: list[Path] = []
            command_classes: list[type[Command]] = []
            for command in commands:
                if isinstance(command, Path):
                    command_paths.append(command)
                    continue

                command_classes.append(command)

            kernel.add_command_paths(command_paths)
            kernel.add_commands(command_classes)

        self._register_commands_callback = _register_commands

        return self

    def with_middleware(self, callback: Callable[[MiddlewareStack], None]) -> Self:
        def configure_middleware(gateway: Gateway) -> None:
            stack = MiddlewareStack()

            callback(stack)

            gateway.set_middleware(stack.middleware)

        self._configure_middleware_stack = configure_middleware

        return self

    def create(self) -> Application:
        from expanse.core.application import Application

        app = Application(self._base_path, container=self._container)
        if self._configure_kernels is not None:
            self._configure_kernels(self._container)

        if self._register_commands_callback is not None:

            def _register_commands(container: Container) -> None:
                from expanse.core.console.kernel import Kernel as ConsoleKernel

                assert self._register_commands_callback is not None

                container.on_resolved(ConsoleKernel, self._register_commands_callback)

            app.bootstrapping(_register_commands)

        if self._configure_middleware_stack:

            def _configure_middleware(container: Container) -> None:
                from expanse.core.http.gateway import Gateway

                assert self._configure_middleware_stack is not None

                container.on_resolved(Gateway, self._configure_middleware_stack)

            app.bootstrapping(_configure_middleware)

        return app
