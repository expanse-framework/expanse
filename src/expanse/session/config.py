from pathlib import Path

from pydantic import BaseModel


class DatabaseStoreConfig(BaseModel):
    # The table that should be used to store the session data.
    table: str = "sessions"

    # The database connection that should be used to store the session data.
    # The value must match one of the configured database connections.
    connection: str | None = None


class FileStoreConfig(BaseModel):
    # The path to the directory where the session data should be stored.
    path: Path = Path("storage/expanse/sessions")


class StoresConfig(BaseModel):
    database: DatabaseStoreConfig = DatabaseStoreConfig()
    dictionary: None = None
    file: FileStoreConfig = FileStoreConfig()
    null: None = None
