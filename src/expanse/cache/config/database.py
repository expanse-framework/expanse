from pydantic import BaseModel


class DatabaseStoreConfig(BaseModel):
    # The table that should be used to store the cache data.
    table: str = "cache"

    # The database connection that should be used to store the cache data.
    # The value must match one of the configured database connections.
    connection: str | None = None

    # Locks table name.
    locks_table: str = "cache_locks"

    # Default TTL for locks in seconds. Defaults to 24 hours.
    locks_default_ttl: int = 86_400
