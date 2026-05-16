from pydantic import BaseModel


class DatabaseStoreConfig(BaseModel):
    # The table that should be used to store the cache data.
    table: str = "cache"

    # The database connection that should be used to store the cache data.
    # The value must match one of the configured database connections.
    connection: str | None = None
