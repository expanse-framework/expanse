from pydantic import BaseModel


class DatabaseStoreConfig(BaseModel):
    # The table that should be used to store the session data.
    table: str = "sessions"

    # The database connection that should be used to store the session data.
    # The value must match one of the configured database connections.
    connection: str | None = None


class StoresConfig(BaseModel):
    database: DatabaseStoreConfig = DatabaseStoreConfig()
    dictionary: None = None
