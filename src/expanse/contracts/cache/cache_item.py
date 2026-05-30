from dataclasses import dataclass
from typing import Any


@dataclass
class CacheItem:
    # The key of the cache item.
    key: str

    # The value of the cache item. This will be None if the cache item is a miss.
    value: Any = None

    # Whether the cache item is a hit or a miss.
    is_hit: bool = False

    # The expiration time of the cache item in seconds.
    expiration: int | None = None
