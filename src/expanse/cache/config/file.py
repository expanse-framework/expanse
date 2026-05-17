from pathlib import Path

from pydantic import BaseModel


class FileStoreConfig(BaseModel):
    # The path to the directory where the cache data should be stored.
    path: Path = Path("storage/cache/data")

    # The permissions that should be set on the cache files and directories.
    permissions: int | None = None
