from dataclasses import dataclass


@dataclass
class CacheItemDeleted:
    key: str
