from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.core.http.middleware.middleware_stack import MiddlewareStack


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from expanse.asynchronous.console.commands.command import Command
    from expanse.asynchronous.core.application import Application
    from expanse.asynchronous.core.console.gateway import Gateway as ConsoleKernel
    from expanse.asynchronous.core.http.gateway import Gateway as HTTPGateway


class ApplicationBuilder:
    def __init__(self, base_path: Path) -> None:
        self._base_path: Path = base_path
        self._container = Container()
        self._register_commands_callback: (
            Callable[[ConsoleKernel], Awaitable[None]] | None
        ) = None
        self._configure_middleware_stack: (
            Callable[[HTTPGateway], Awaitable[None]] | None
        ) = None
        self._configure_kernels: Callable[[Container], None] | None = None

    def with_kernels(self) -> Self:
        def configure_kernels(container: Container) -> None:
            from expanse.asynchronous.core.console.gateway import Gateway

            container.singleton(Gateway)

        self._configure_kernels = configure_kernels

        return self

    def with_commands(self, commands: list[type[Command] | Path] | None = None) -> Self:
        async def _register_commands(kernel: ConsoleKernel) -> None:
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

    def with_middleware(
        self, callback: Callable[[MiddlewareStack], Awaitable[None]]
    ) -> Self:
        async def configure_middleware(gateway: HTTPGateway) -> None:
            stack = MiddlewareStack()

            await callback(stack)

            gateway.set_middleware(stack.middleware)

        self._configure_middleware_stack = configure_middleware

        return self

    def create(self) -> Application:
        from expanse.asynchronous.core.application import Application

        app = Application(self._base_path, container=self._container)
        if self._configure_kernels is not None:
            self._configure_kernels(self._container)

        if self._register_commands_callback is not None:

            async def _register_commands(container: Container) -> None:
                from expanse.asynchronous.core.console.gateway import (
                    Gateway as ConsoleGateway,
                )

                assert self._register_commands_callback is not None

                await container.on_resolved(
                    ConsoleGateway, self._register_commands_callback
                )

            app.bootstrapping(_register_commands)

        if self._configure_middleware_stack:

            async def _configure_middleware(container: Container) -> None:
                from expanse.asynchronous.core.http.gateway import Gateway

                assert self._configure_middleware_stack is not None

                await container.on_resolved(Gateway, self._configure_middleware_stack)

            app.bootstrapping(_configure_middleware)

        return app
