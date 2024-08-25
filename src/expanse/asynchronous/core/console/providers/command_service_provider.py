from collections.abc import Callable
from importlib import import_module
from typing import ClassVar

from expanse.asynchronous.console.commands.command import Command
from expanse.asynchronous.core.console.gateway import Gateway as ConsoleKernel
from expanse.asynchronous.support.service_provider import ServiceProvider


class CommandServiceProvider(ServiceProvider):
    COMMANDS: ClassVar[list[str]] = ["routes list", "serve"]

    async def register(self) -> None:
        # TODO: register commands only on starting event once implemented

        console = (await self._container.make(ConsoleKernel)).console

        for command in self.COMMANDS:
            console.command_loader.register_factory(
                command, self._load_command(command)
            )

    def _load_command(self, name: str) -> Callable[[], Command]:
        def _load() -> Command:
            words = name.split(" ")
            module = import_module(
                "expanse.asynchronous.core.console.commands." + ".".join(words)
            )
            command_class = getattr(
                module, "".join(c.title() for c in words) + "Command"
            )
            command: Command = command_class()
            return command

        return _load
