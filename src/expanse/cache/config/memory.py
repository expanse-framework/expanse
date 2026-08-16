from pydantic import BaseModel

from expanse.support.size import Size


class MemoryStoreConfig(BaseModel):
    # The maximum number of items that should be stored in the cache.
    # If the cache exceeds this limit, the least recently used items will be evicted.
    max_items: int = 1000

    # The maximum size of the cache (e.g. "64mb", "1gb").
    # If the cache exceeds this limit, the least recently used items will be evicted.
    max_size: Size | None = None

    # The default time-to-live (TTL) for cache items in seconds.
    # If not set, cache items will never expire.
    default_ttl: int | None = None
