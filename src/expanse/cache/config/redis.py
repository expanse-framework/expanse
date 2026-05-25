from pydantic import BaseModel


class RedisStoreConfig(BaseModel):
    # The name of the Redis connection.
    connection: str

    # The name of the connection used for locks. If not provided, the same connection will be used for locks.
    lock_connection: str | None = None
