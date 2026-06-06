from pydantic import BaseModel


class MemoryStoreConfig(BaseModel):
    # The maximum number of items that should be stored in the cache.
    # If the cache exceeds this limit, the least recently used items will be evicted.
    max_items: int = 1000

    # The maximum size of the cache in bytes.
    # If the cache exceeds this limit, the least recently used items will be evicted.
    max_size: int | None = None

    # The default time-to-live (TTL) for cache items in seconds.
    # If not set, cache items will never expire.
    default_ttl: int | None = None
