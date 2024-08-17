from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol


if TYPE_CHECKING:
    from expanse.testing.command_tester import TestingCommand


class TestingCommandHelper(Protocol):
    def __call__(self, name: str, parameters: str | None = None) -> TestingCommand: ...
