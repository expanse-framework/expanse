from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.core.application import Application


class ServiceProvider:
    def __init__(self, app: Application) -> None:
        self._app: Application = app

    def register(self) -> None:
        """
        Register any application services.
        """
