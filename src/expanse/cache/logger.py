from logging import NOTSET
from logging import Logger as BaseLogger


class Logger(BaseLogger):
    def __init__(self, name: str, level=NOTSET) -> None:
        super().__init__(name, level)

    def l1_hit(self, store: str, key: str) -> None:
        self.debug("L1 cache hit", extra={"store": store, "key": key})

    def l2_hit(self, store: str, key: str) -> None:
        self.debug("L2 cache hit", extra={"store": store, "key": key})

    def l2_miss(self, store: str, key: str) -> None:
        self.debug("L2 cache miss", extra={"store": store, "key": key})

    def miss(self, store: str, key: str) -> None:
        self.debug("Cache miss", extra={"store": store, "key": key})

    def hit(self, store: str, key: str) -> None:
        self.debug("Cache hit", extra={"store": store, "key": key})

    def delete(self, store: str, key: str) -> None:
        self.debug("Cache deleted", extra={"store": store, "key": key})

    def clear(self, store: str) -> None:
        self.debug("Cache cleared", extra={"store": store})
