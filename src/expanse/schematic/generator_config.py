from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.routing.route import Route


class GeneratorConfig:
    """
    Configuration for the OpenAPI generator.

    Provides settings for filtering routes, customizing output, and configuring
    the generation process.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the generator configuration.

        Args:
            config: Configuration dictionary
        """
        self._config: dict[str, Any] = config or {}
        self._routes_filter: Callable[[Route], bool] = self._default_routes_filter

    def filter_routes(self, route: Route) -> bool:
        """
        Check if a route should be included in the generated specification.

        Args:
            route: The route to check

        Returns:
            True if the route should be included, False otherwise
        """
        return self._routes_filter(route)

    def set_routes_filter(self, filter_func: Callable[[Route], bool]) -> None:
        """
        Set a custom route filter function.

        Args:
            filter_func: Function that takes a Route and returns bool
        """
        self._routes_filter = filter_func

    def _default_routes_filter(self, route: Route) -> bool:
        """
        Default filter: include routes that start with the configured API path.

        Args:
            route: The route to check

        Returns:
            True if the route should be included
        """
        prefix = self._config.get("api_path", "/api").rstrip("/")

        return route.path.startswith(f"{prefix}/") or route.path == prefix

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation like "info.title")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation like "info.title")
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
