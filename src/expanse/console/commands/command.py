from __future__ import annotations

from typing import IO
from typing import TYPE_CHECKING

from cleo.commands.command import Command as BaseCommand


if TYPE_CHECKING:
    from expanse.core.application import Application as Expanse


class Command(BaseCommand):
    _expanse: Expanse | None = None

    def handle(self, *args, **kwargs) -> int:
        raise NotImplementedError()

    def execute(self, io: IO) -> int:
        self._io = io

        try:
            if not self._expanse:
                return self.handle()

            return self._expanse.call(self.handle)
        except KeyboardInterrupt:
            return 1

    def set_expanse(self, expanse: Expanse) -> None:
        self._expanse = expanse
