from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Self

from expanse.common.foundation.helpers import PlaceholderPath


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.common.configuration.config import Config
    from expanse.foundation.http.middleware.base import Middleware
    from expanse.support.service_provider import ServiceProvider


class Application:
    def __init__(self, base_path: Path) -> None:
        super().__init__()

        self._base_path: Path = base_path
        self._config_path: Path | None = None
        self._resources_path: Path | None = None
        self._environment_path: Path | None = None
        self._database_path: Path | None = None

        self._booted: bool = False
        self._has_been_bootstrapped: bool = False
        self._service_providers: list[ServiceProvider] = []
        self._config: Config

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def config_path(self) -> Path:
        return self._config_path or self._base_path.joinpath("config")

    @property
    def resources_path(self) -> Path:
        return self._resources_path or self._base_path.joinpath("resources")

    @property
    def database_path(self) -> Path:
        return self._database_path or self._base_path.joinpath("database")

    @property
    def environment_path(self) -> Path:
        return self._environment_path or self._base_path

    @property
    def environment_file(self) -> str:
        return ".env"

    @property
    def config(self) -> Config:
        return self._config

    def set_config(self, config: Config) -> None:
        self._config = config

    def resolve_placeholder_path(self, path: str | Path | PlaceholderPath) -> Path:
        if not isinstance(path, PlaceholderPath):
            return path

        app_path: Path = getattr(self, f"{path.app_path}_path")

        return app_path.joinpath(path.relative_path)

    def is_booted(self) -> bool:
        return self._booted

    def has_been_bootstrapped(self) -> bool:
        return self._has_been_bootstrapped

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        return self

    def prepend_middleware(self, middleware: type[Middleware]) -> None:
        self._default_middlewares.insert(0, middleware)

    def add_middleware(self, middleware: type[Middleware]) -> None:
        self._default_middlewares.append(middleware)
