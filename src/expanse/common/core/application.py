from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Self


if TYPE_CHECKING:
    from pathlib import Path

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
    def environment_path(self) -> Path:
        return self._environment_path or self._base_path

    def path(self, path: str | Path, relative: bool = False) -> Path:
        path = self._base_path.joinpath("app").joinpath(path)

        if relative:
            path = path.relative_to(self._base_path)

        return path

    def named_path(self, name: str) -> Path:
        path_key = f"paths.{name}"
        if path_key not in self._config:
            raise ValueError(f"Named path {name} is not configured.")

        path: Path = self._config[path_key]

        return self._base_path.joinpath(path)

    @property
    def environment_file(self) -> str:
        return ".env"

    @property
    def config(self) -> Config:
        return self._config

    def set_config(self, config: Config) -> None:
        self._config = config

    def is_booted(self) -> bool:
        return self._booted

    def has_been_bootstrapped(self) -> bool:
        return self._has_been_bootstrapped

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        return self
