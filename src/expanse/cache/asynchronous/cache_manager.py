from datetime import datetime
from typing import Any
from typing import overload
from typing import override

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.cache.asynchronous.store import Store


class CacheManager(CacheContract):
    def __init__(self, config: Config, container: Container):
        self._config: Config = config
        self._container: Container = container
        self._caches: dict[str, CacheContract] = {}

    async def cache(self, name: str | None = None) -> CacheContract:
        if name is None:
            name = self.get_default_store_name()

        if name in self._caches:
            return self._caches[name]

        store = await self._create_store(name)

        self._caches[name] = Cache(store)

        return self._caches[name]

    def get_default_store_name(self) -> str:
        default_store: str | None = self._config.get("cache.store")
        if default_store is None:
            raise NoDefaultStoreError("No default cache store configured.")

        return default_store

    async def _create_store(self, name: str) -> Store:
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

            case "database":
                return await self._create_database_store(store_config)

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported cache store driver '{store_config['driver']}' for store '{name}'."
                )

    def _create_memory_store(self) -> Store:
        from expanse.cache.asynchronous.stores.memory import MemoryStore
        from expanse.cache.synchronous.stores.memory import (
            MemoryStore as SyncMemoryStore,
        )

        return MemoryStore(SyncMemoryStore())

    async def _create_database_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.asynchronous.stores.database.store import DatabaseStore
        from expanse.cache.config.database import DatabaseStoreConfig
        from expanse.database.asynchronous.database_manager import AsyncDatabaseManager

        config = DatabaseStoreConfig.model_validate(store_config)

        db = await self._container.get(AsyncDatabaseManager)

        return DatabaseStore(config, db)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        cache = await self.cache()

        return await cache.set(key, value, ttl, until)

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        cache = await self.cache()

        return await cache.set_many(items, ttl, until)

    @overload
    async def get(self, key: str) -> Any | None: ...

    @overload
    async def get(self, key: str, default: Any) -> Any: ...

    @override
    async def get(self, key: str, default: Any | None = None) -> Any | None:
        cache = await self.cache()

        return await cache.get(key, default)

    @override
    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        cache = await self.cache()

        return await cache.get_many(keys)

    @override
    async def has(self, key: str) -> bool:
        cache = await self.cache()

        return await cache.has(key)

    @override
    async def pop(self, key: str) -> Any | None:
        cache = await self.cache()

        return await cache.pop(key)

    @override
    async def delete(self, key: str) -> bool:
        cache = await self.cache()

        return await cache.delete(key)

    @override
    async def delete_many(self, keys: list[str]) -> bool:
        cache = await self.cache()

        return await cache.delete_many(keys)

    @override
    async def clear(self) -> bool:
        cache = await self.cache()

        return await cache.clear()
