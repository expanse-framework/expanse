from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class LocalStorageConfig(BaseSettings):
    driver: Literal["local"] = "local"

    # The root directory where the files should be stored.
    root: Path = Path("storage")
