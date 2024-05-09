from __future__ import annotations

from typing import TYPE_CHECKING

from dotenv import load_dotenv


if TYPE_CHECKING:
    from expanse.core.application import Application


class LoadEnvironmentVariables:
    @classmethod
    def bootstrap(cls, app: Application) -> None:
        env_file = app.environment_path.joinpath(app.environment_file)

        if env_file.exists():
            load_dotenv(env_file)
