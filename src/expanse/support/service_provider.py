from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.container.container import Container


class ServiceProvider:
    def __init__(self, container: Container) -> None:
        self._container: Container = container

    def register(self) -> None:
        """
        Register any application services.
        """
