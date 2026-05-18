from pydantic import BaseModel


class RedisStoreConfig(BaseModel):
    # The name of the Redis connection.
    connection: str
