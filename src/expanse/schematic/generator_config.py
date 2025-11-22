from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.routing.route import Route


class GeneratorConfig:
    """
    Configuration for the OpenAPI generator.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = config or {}
        self._routes_filter: Callable[[Route], bool] = self._default_routes_filter

    def filter_routes(self, route: Route) -> bool:
        return self._routes_filter(route)

    def set_routes_filter(self, filter_func: Callable[[Route], bool]) -> None:
        self._routes_filter = filter_func

    def _default_routes_filter(self, route: Route) -> bool:
        prefix = self._config.get("api_path", "/api").rstrip("/")

        return route.path.startswith(f"{prefix}/") or route.path == prefix

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
