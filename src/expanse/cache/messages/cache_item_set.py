from dataclasses import dataclass


@dataclass
class CacheItemSet:
    keys: list[str]
