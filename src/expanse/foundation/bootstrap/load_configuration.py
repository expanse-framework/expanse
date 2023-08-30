from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from expanse.support._utils import module_from_path


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.foundation.application import Application


class LoadConfiguration:
    @classmethod
    def bootstrap(cls, app: Application) -> None:
        config = {}

        files = cls._get_configuration_files(app)

        if "app" not in files:
            raise Exception('Unable to load the "app" configuration file')

        for identifier, filepath in files.items():
            config[identifier] = cls._load_configuration_file(filepath)

        app.instance("config", config)

    @classmethod
    def _get_configuration_files(cls, app: Application) -> dict[str, Path]:
        files = {}

        for filepath in app.config_path.rglob("*.py"):
            files[
                filepath.relative_to(app.config_path)
                .with_suffix("")
                .as_posix()
                .replace("/", ":")
            ] = filepath

        return dict(sorted(files.items()))

    @classmethod
    def _load_configuration_file(cls, path: Path) -> dict[str, Any]:
        module = module_from_path(path)

        if module is None:
            return {}

        config = module.config

        assert isinstance(config, dict)

        return config
