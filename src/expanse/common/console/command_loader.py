from __future__ import annotations

from collections.abc import Callable
from typing import Generic
from typing import TypeVar

from cleo.exceptions import CleoCommandNotFoundError
from cleo.exceptions import CleoLogicError

from expanse.common.console.command import Command


TCommand = TypeVar("TCommand", bound=Command)
Factory = Callable[[], TCommand]


class CommandLoader(Generic[TCommand]):
    def __init__(self, factories: dict[str, Factory]) -> None:
        self._factories = factories

    @property
    def names(self) -> list[str]:
        return list(self._factories.keys())

    def has(self, name: str) -> bool:
        return name in self._factories

    def get(self, name: str) -> TCommand:
        if name not in self._factories:
            raise CleoCommandNotFoundError(name)

        factory = self._factories[name]

        return factory()

    def register_factory(
        self, command_name: str, factory: Callable[[], TCommand]
    ) -> None:
        if command_name in self._factories:
            raise CleoLogicError(f'The command "{command_name}" already exists.')

        self._factories[command_name] = factory
