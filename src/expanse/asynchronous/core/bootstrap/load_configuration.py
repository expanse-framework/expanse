from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from pydantic_settings import BaseSettings

from expanse.common.configuration.config import Config
from expanse.common.support._utils import module_from_path


if TYPE_CHECKING:
    from expanse.asynchronous.core.application import Application


class LoadConfiguration:
    @classmethod
    async def bootstrap(cls, app: Application) -> None:
        config = Config({})

        base_files = await cls._get_base_configuration_files(app)
        for identifier, filepath in base_files.items():
            config[identifier] = await cls._load_configuration_file(filepath)

        files = await cls._get_configuration_files(app)

        for identifier, filepath in files.items():
            for name, value in (await cls._load_configuration_file(filepath)).items():
                config[f"{identifier}.{name}"] = value

        app.set_config(config)

    @classmethod
    async def _get_configuration_files(cls, app: Application) -> dict[str, Path]:
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
    async def _load_configuration_file(cls, path: Path) -> dict[str, Any]:
        module = module_from_path(path)

        if module is None:
            return {}

        if hasattr(module, "Config") and issubclass(module.Config, BaseSettings):
            config = module.Config().model_dump()
        else:
            config = module.config

        assert isinstance(config, dict)

        return config

    @classmethod
    async def _get_base_configuration_files(cls, app: Application) -> dict[str, Path]:
        files = {}

        config_assets_path = Path(__file__).parent.parent.parent.joinpath(
            "assets/config"
        )

        for filepath in config_assets_path.rglob("*.py"):
            files[
                filepath.relative_to(config_assets_path)
                .with_suffix("")
                .as_posix()
                .replace("/", ":")
            ] = filepath

        return dict(sorted(files.items()))
