from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.core.application import Application


class BootProviders:
    @classmethod
    def bootstrap(cls, app: Application) -> None:
        app.boot()
