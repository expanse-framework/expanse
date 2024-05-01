from collections.abc import Callable
from importlib import import_module
from typing import ClassVar

from expanse.console.commands.command import Command
from expanse.foundation.console.kernel import Kernel as ConsoleKernel
from expanse.support.service_provider import ServiceProvider


class CommandServiceProvider(ServiceProvider):
    COMMANDS: ClassVar[list[str]] = ["serve"]

    def register(self) -> None:
        # TODO: register commands only on starting event once implemented

        console = self._app.make(ConsoleKernel).console

        for command in self.COMMANDS:
            console.command_loader.register_factory(
                command, self._load_command(command)
            )

    def _load_command(self, name: str) -> Callable[[], Command]:
        def _load() -> Command:
            words = name.split(" ")
            module = import_module(
                "expanse.foundation.console.commands." + ".".join(words)
            )
            command_class = getattr(
                module, "".join(c.title() for c in words) + "Command"
            )
            command: Command = command_class()
            return command

        return _load