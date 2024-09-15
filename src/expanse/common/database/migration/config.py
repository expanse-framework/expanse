import os
import sys

from argparse import Namespace
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from typing import TextIO

from alembic import util
from alembic.config import Config as AlembicConfig

from expanse.common.core.application import Application


class Config(AlembicConfig):
    def __init__(
        self,
        app: Application,
        file_: str | os.PathLike[str] | None = None,
        ini_section: str = "alembic",
        output_buffer: TextIO | None = None,
        stdout: TextIO = sys.stdout,
        cmd_opts: Namespace | None = None,
        config_args: Mapping[str, Any] = util.immutabledict(),
        attributes: dict[str, Any] | None = None,
    ):
        super().__init__(
            file_=file_
            or app.named_path("database").joinpath("migrations/alembic.ini"),
            ini_section=ini_section,
            output_buffer=output_buffer,
            stdout=stdout,
            cmd_opts=cmd_opts,
            config_args=config_args,
            attributes=attributes,
        )

        self.template_dir = Path(__file__).parent.joinpath("templates")

    def get_template_directory(self) -> str:
        return str(self.template_dir)
