from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.asynchronous.core.application import Application


class BootProviders:
    @classmethod
    async def bootstrap(cls, app: Application) -> None:
        await app.boot()
