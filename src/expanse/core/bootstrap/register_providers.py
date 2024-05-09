from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.core.application import Application


class RegisterProviders:
    @classmethod
    def bootstrap(cls, app: Application) -> None:
        app.register_configured_providers()
