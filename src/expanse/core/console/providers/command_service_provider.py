from collections.abc import Callable
from importlib import import_module
from typing import ClassVar

from expanse.console.commands.command import Command
from expanse.core.console.gateway import Gateway as ConsoleKernel
from expanse.support.service_provider import ServiceProvider


class CommandServiceProvider(ServiceProvider):
    COMMANDS: ClassVar[list[str]] = [
        "make controller",
        "make middleware",
        "routes list",
        "serve",
    ]

    async def register(self) -> None:
        # TODO: register commands only on starting event once implemented

        console = (await self._container.get(ConsoleKernel)).console

        for command in self.COMMANDS:
            console.command_loader.register_factory(
                command, self._load_command(command)
            )

    def _load_command(self, name: str) -> Callable[[], Command]:
        def _load() -> Command:
            words = name.split(" ")
            module = import_module("expanse.core.console.commands." + ".".join(words))
            command_class = getattr(
                module, "".join(c.title() for c in words) + "Command"
            )
            command: Command = command_class()
            return command

        return _load
