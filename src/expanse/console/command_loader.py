from __future__ import annotations

from collections.abc import Callable

from cleo.exceptions import CleoCommandNotFoundError
from cleo.exceptions import CleoLogicError

from expanse.console.commands.command import Command


Factory = Callable[[], Command]


class CommandLoader:
    def __init__(self, factories: dict[str, Factory]) -> None:
        self._factories = factories

    @property
    def names(self) -> list[str]:
        return list(self._factories.keys())

    def has(self, name: str) -> bool:
        return name in self._factories

    def get(self, name: str) -> Command:
        if name not in self._factories:
            raise CleoCommandNotFoundError(name)

        factory = self._factories[name]

        return factory()

    def register_factory(self, command_name: str, factory: Factory) -> None:
        if command_name in self._factories:
            raise CleoLogicError(f'The command "{command_name}" already exists.')

        self._factories[command_name] = factory
