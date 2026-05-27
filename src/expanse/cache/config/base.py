from pydantic import BaseModel
from pydantic import Field


class L1CacheConfig(BaseModel):
    # The maximum number of items that should be stored in the L1 cache.
    max_items: int = 1000

    # The maximum size of the L1 cache in bytes.
    max_size: int | None = None


class BaseConfig(BaseModel):
    l1_cache: L1CacheConfig = Field(default_factory=L1CacheConfig)
