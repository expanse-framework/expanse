from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Self

from expanse.common.core.helpers import PlaceholderPath


if TYPE_CHECKING:
    from expanse.common.configuration.config import Config


class Application:
    def __init__(self, base_path: Path) -> None:
        super().__init__()

        self._base_path: Path = base_path
        self._config_path: Path | None = None
        self._resources_path: Path | None = None
        self._static_path: Path | None = None
        self._environment_path: Path | None = None
        self._database_path: Path | None = None

        self._booted: bool = False
        self._has_been_bootstrapped: bool = False
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
    def static_path(self) -> Path:
        return self._static_path or self._base_path.joinpath("static")

    @property
    def database_path(self) -> Path:
        return self._database_path or self._base_path.joinpath("database")

    @property
    def environment_path(self) -> Path:
        return self._environment_path or self._base_path

    def path(self, path: str | Path) -> Path:
        return self._base_path.joinpath("app").joinpath(path)

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
            return Path(path)

        app_path: Path = getattr(self, f"{path.app_path}_path")

        return app_path.joinpath(path.relative_path)

    def is_booted(self) -> bool:
        return self._booted

    def has_been_bootstrapped(self) -> bool:
        return self._has_been_bootstrapped

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        return self
