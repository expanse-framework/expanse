from __future__ import annotations

from typing import IO
from typing import TYPE_CHECKING

from expanse.asynchronous.console._adapters.command import Command as BaseCommand


if TYPE_CHECKING:
    from expanse.asynchronous.core.application import Application as Expanse


class Command(BaseCommand):
    _expanse: Expanse | None = None

    async def execute(self, io: IO) -> int:
        self._io = io

        try:
            if not self._expanse:
                return await self.handle()

            return await self._expanse.call(self.handle)
        except KeyboardInterrupt:
            return 1

    def set_expanse(self, expanse: Expanse) -> None:
        self._expanse = expanse
