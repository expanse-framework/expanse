from datetime import datetime
from typing import Any
from typing import overload
from typing import override

from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.cache.synchronous.cache import Cache
from expanse.configuration.config import Config
from expanse.contracts.cache.synchronous.cache import Cache as CacheContract
from expanse.contracts.cache.synchronous.store import Store


class CacheManager(CacheContract):
    def __init__(self, config: Config):
        self._config: Config = config
        self._caches: dict[str, CacheContract] = {}

    def cache(self, name: str | None = None) -> CacheContract:
        if name is None:
            name = self.get_default_store_name()

        if name in self._caches:
            return self._caches[name]

        store = self._create_store(name)

        self._caches[name] = Cache(store)

        return self._caches[name]

    def get_default_store_name(self) -> str:
        default_store: str | None = self._config.get("cache.store")
        if default_store is None:
            raise NoDefaultStoreError("No default cache store configured.")

        return default_store

    def _create_store(self, name: str) -> Store:
        stores: dict[str, dict[str, Any]] = self._config.get("cache.stores", {})
        if name not in stores:
            raise UnconfiguredStoreError(f"Cache store '{name}' is not configured.")

        store_config = stores[name]

        if "driver" not in store_config:
            raise UnconfiguredStoreError(
                f"Cache store '{name}' is missing a driver configuration."
            )

        match store_config["driver"]:
            case "memory":
                return self._create_memory_store()

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported cache store driver '{store_config['driver']}' for store '{name}'."
                )

    def _create_memory_store(self) -> Store:
        from expanse.cache.synchronous.stores.memory import MemoryStore

        return MemoryStore()

    @override
    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        return self.cache().set(key, value, ttl, until)

    @override
    def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        return self.cache().set_many(items, ttl, until)

    @overload
    def get(self, key: str) -> Any | None: ...

    @overload
    def get(self, key: str, default: Any) -> Any: ...

    @override
    def get(self, key: str, default: Any | None = None) -> Any | None:
        return self.cache().get(key, default)

    @override
    def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        return self.cache().get_many(keys)

    @override
    def has(self, key: str) -> bool:
        return self.cache().has(key)

    @override
    def pop(self, key: str) -> Any | None:
        return self.cache().pop(key)

    @override
    def delete(self, key: str) -> bool:
        return self.cache().delete(key)

    @override
    def delete_many(self, keys: list[str]) -> bool:
        return self.cache().delete_many(keys)

    @override
    def clear(self) -> bool:
        return self.cache().clear()
