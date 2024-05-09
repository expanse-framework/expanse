from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.asynchronous.core.application import Application


class RegisterProviders:
    @classmethod
    async def bootstrap(cls, app: Application) -> None:
        await app.register_configured_providers()
