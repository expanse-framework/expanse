from dataclasses import dataclass


@dataclass
class CacheItemDeleted:
    keys: list[str]
