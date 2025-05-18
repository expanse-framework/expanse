from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from expanse.container.container import Container
from expanse.core.http.middleware.middleware_stack import MiddlewareStack


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from expanse.console.commands.command import Command
    from expanse.core.application import Application
    from expanse.core.console.portal import Portal as ConsolePortal
    from expanse.core.http.portal import Portal as HTTPPortal


class ApplicationBuilder:
    def __init__(self, base_path: Path) -> None:
        self._base_path: Path = base_path
        self._container = Container()
        self._register_commands_callback: (
            Callable[[ConsolePortal], Awaitable[None]] | None
        ) = None
        self._configure_middleware_stack: (
            Callable[[HTTPPortal], Awaitable[None]] | None
        ) = None
        self._configure_portals: Callable[[Container], None] | None = None

    def with_portals(self) -> Self:
        def configure_portals(container: Container) -> None:
            from expanse.core.console.portal import Portal

            container.singleton(Portal)

        self._configure_portals = configure_portals

        return self

    def with_commands(self, commands: list[type[Command] | Path] | None = None) -> Self:
        async def _register_commands(portal: ConsolePortal) -> None:
            nonlocal commands

            if not commands:
                commands = [portal._app.path("console/commands")]

            command_paths: list[Path] = []
            command_classes: list[type[Command]] = []
            for command in commands:
                if isinstance(command, Path):
                    command_paths.append(command)
                    continue

                command_classes.append(command)

            portal.add_command_paths(command_paths)
            portal.add_commands(command_classes)

        self._register_commands_callback = _register_commands

        return self

    def with_middleware(
        self, callback: Callable[[MiddlewareStack], Awaitable[None]]
    ) -> Self:
        async def configure_middleware(portal: HTTPPortal) -> None:
            stack = MiddlewareStack()

            await callback(stack)

            portal.set_middleware(stack.middleware)
            portal.set_middleware_groups(stack.groups)

        self._configure_middleware_stack = configure_middleware

        return self

    def create(self) -> Application:
        from expanse.core.application import Application

        app = Application(self._base_path, container=self._container)
        if self._configure_portals is not None:
            self._configure_portals(self._container)

        if self._register_commands_callback is not None:

            async def _register_commands(container: Container) -> None:
                from expanse.core.console.portal import Portal as ConsolePortal

                assert self._register_commands_callback is not None

                await container.on_resolved(
                    ConsolePortal, self._register_commands_callback
                )

            app.bootstrapping(_register_commands)

        if self._configure_middleware_stack:

            async def _configure_middleware(container: Container) -> None:
                from expanse.core.http.portal import Portal

                assert self._configure_middleware_stack is not None

                await container.on_resolved(Portal, self._configure_middleware_stack)

            app.bootstrapping(_configure_middleware)

        return app
