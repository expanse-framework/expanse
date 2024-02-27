from cleo.application import Application
from cleo.commands.command import Command as BaseCleoCommand
from cleo.io.io import IO

from expanse.asynchronous.console._adapters.command import Command


class WrappedCommand(Command):
    def __init__(self, wrapped: BaseCleoCommand) -> None:
        self._wrapped = wrapped
        super().__init__()
        self.name = wrapped.name
        self.description = wrapped.description
        self.help = wrapped.help
        self.arguments = wrapped.arguments
        self.options = wrapped.options
        self._definition = wrapped.definition

    def set_application(self, application: Application | None = None) -> None:
        super().set_application(application)

        self._wrapped.set_application(application)

    async def run(self, io: IO) -> int:
        return self._wrapped.run(io)
