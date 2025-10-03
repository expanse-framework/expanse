from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypedDict


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.routing.route import Route


class Config(TypedDict):
    api_path: str


class GeneratorConfig:
    def __init__(self, config: Config) -> None:
        self._config: Config = config
        self._routes_filter: Callable[[Route], bool] = self._default_routes_filter

    def filter_routes(self, route: Route) -> bool:
        return self._routes_filter(route)

    def _default_routes_filter(self, route: Route) -> bool:
        prefix = self._config.get("api_path", "/api").rstrip("/")

        return route.path.startswith(f"{prefix}/") or route.path == f"/{prefix}"
