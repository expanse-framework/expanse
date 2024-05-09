from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from cleo.commands.completions_command import CompletionsCommand
from cleo.commands.help_command import HelpCommand
from cleo.commands.list_command import ListCommand
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_events import COMMAND
from cleo.events.event_dispatcher import EventDispatcher

from expanse.__version__ import __version__
from expanse.asynchronous.console._adapters.application import (
    Application as BaseApplication,
)
from expanse.asynchronous.console._adapters.wrapped_command import WrappedCommand
from expanse.asynchronous.console.command_loader import CommandLoader
from expanse.asynchronous.console.commands.command import Command


if TYPE_CHECKING:
    from cleo.events.event import Event

    from expanse.asynchronous.console._adapters.command import Command as AdapterCommand
    from expanse.asynchronous.core.application import Application as Expanse


class Application(BaseApplication):
    def __init__(self, expanse: Expanse) -> None:
        super().__init__("expanse", __version__)

        self._expanse = expanse

        dispatcher = EventDispatcher()
        dispatcher.add_listener(COMMAND, self._set_expanse)
        self.set_event_dispatcher(dispatcher)

        command_loader = CommandLoader({})
        self.set_command_loader(command_loader)

    @property
    def default_commands(self) -> list[AdapterCommand]:
        return [
            WrappedCommand(HelpCommand()),
            WrappedCommand(ListCommand()),
            WrappedCommand(CompletionsCommand()),
        ]

    @property
    def command_loader(self) -> CommandLoader:
        return self._command_loader

    def _set_expanse(self, event: Event, event_name: str, _: EventDispatcher) -> None:
        assert isinstance(event, ConsoleCommandEvent)

        command = event.command

        if not isinstance(command, Command):
            return

        command = cast(Command, command)

        command.set_expanse(self._expanse)
