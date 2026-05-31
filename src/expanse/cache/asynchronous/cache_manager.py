import logging

from typing import Any
from typing import cast

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.cache_stack import CacheStack
from expanse.cache.config.locker import LockerConfig
from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredL1CacheBusError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedL1CacheBusDriverError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.cache.asynchronous.locker import Locker
from expanse.contracts.cache.asynchronous.store import Store
from expanse.core.application import Application


logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, app: Application, config: Config, container: Container):
        self._app: Application = app
        self._config: Config = config
        self._container: Container = container
        self._caches: dict[str, CacheContract] = {}

    async def cache(self, name: str | None = None) -> CacheContract:
        if name is None:
            name = self.get_default_store_name()

        if name in self._caches:
            return self._caches[name]

        cache = await self._create_cache(name)

        self._caches[name] = cache

        return self._caches[name]

    def get_default_store_name(self) -> str:
        default_store: str | None = self._config.get("cache.store")
        if default_store is None:
            raise NoDefaultStoreError("No default cache store configured.")

        return default_store

    async def _create_cache(self, name: str) -> CacheContract:
        stores: dict[str, dict[str, Any]] = self._config.get("cache.stores", {})
        if name not in stores:
            raise UnconfiguredStoreError(f"Cache store '{name}' is not configured.")

        store_config = stores[name]

        if "driver" not in store_config:
            raise UnconfiguredStoreError(
                f"Cache store '{name}' is missing a driver configuration."
            )

        store = await self._create_store(name, store_config)

        raw_locker_config = self._config.get("cache.locker", None)
        locker = await self._create_locker(raw_locker_config)

        l1_cache_config = store_config.get("l1_cache", None)

        if not l1_cache_config:
            logger.debug(
                "Creating single-level cache",
                extra={"store": name, "driver": store_config["driver"]},
            )
            return Cache(name, store, locker=locker)

        l1_store_config = l1_cache_config.get("store", None)
        if not l1_store_config:
            raise UnconfiguredStoreError(
                f"L1 cache configuration for store '{name}' is missing a store configuration."
            )

        l1_store = await self._create_l1_store(l1_store_config)

        l1_bus_config = l1_cache_config.get("bus", None)
        if not l1_bus_config:
            l1_bus_config = {"driver": "memory"}

        bus = await self._create_bus(l1_bus_config)

        logger.debug(
            "Creating two-level cache",
            extra={
                "store": name,
                "l1": l1_store_config["driver"],
                "l2": store_config["driver"],
                "bus": l1_bus_config["driver"],
            },
        )
        return CacheStack(f"{name}", l1_store, store, bus, locker=locker)

    async def _create_store(self, name: str, store_config: dict[str, Any]) -> Store:
        match store_config["driver"]:
            case "memory":
                return await self._create_memory_store(name)

            case "database":
                return await self._create_database_store(store_config)

            case "file":
                return await self._create_file_store(store_config)

            case "redis":
                return await self._create_redis_store(store_config)

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported cache store driver '{store_config['driver']}' for store '{name}'."
                )

    async def _create_l1_store(self, l1_cache_config: dict[str, Any]) -> Store:
        if "driver" not in l1_cache_config:
            raise UnconfiguredStoreError("L1 cache configuration is missing a driver.")

        match l1_cache_config["driver"]:
            case "memory":
                return await self._create_memory_store()

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported L1 cache store driver '{l1_cache_config['driver']}'."
                )

    async def _create_memory_store(self, name: str | None = None) -> Store:
        from expanse.cache.asynchronous.stores.memory import MemoryStore
        from expanse.cache.synchronous.cache_manager import (
            CacheManager as SyncCacheManager,
        )
        from expanse.cache.synchronous.stores.memory import (
            MemoryStore as SyncMemoryStore,
        )

        if name is None or not self._container.has(SyncCacheManager):
            return MemoryStore(SyncMemoryStore())

        sync_cache_manager = await self._container.get(SyncCacheManager)
        sync_cache = await sync_cache_manager.cache(name)
        sync_store: SyncMemoryStore = cast("SyncMemoryStore", sync_cache._store)

        return MemoryStore(sync_store)

    async def _create_database_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.asynchronous.stores.database.store import DatabaseStore
        from expanse.cache.config.database import DatabaseStoreConfig
        from expanse.database.asynchronous.database_manager import AsyncDatabaseManager

        config = DatabaseStoreConfig.model_validate(store_config)

        db = await self._container.get(AsyncDatabaseManager)

        return DatabaseStore(config, db)

    async def _create_file_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.asynchronous.stores.file.store import FileStore
        from expanse.cache.config.file import FileStoreConfig
        from expanse.cache.synchronous.stores.file.store import (
            FileStore as SyncFileStore,
        )

        config = FileStoreConfig.model_validate(store_config)

        path = config.path
        if not path.is_absolute():
            path = self._app.base_path.joinpath(path)

        locks_path = config.locks_path
        if locks_path is not None and not locks_path.is_absolute():
            locks_path = self._app.base_path.joinpath(locks_path)

        sync_store = SyncFileStore(
            config.path, config.permissions, locks_path=config.locks_path
        )

        return FileStore(sync_store)

    async def _create_redis_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.asynchronous.stores.redis.store import RedisStore
        from expanse.cache.config.redis import RedisStoreConfig
        from expanse.redis.asynchronous.redis_manager import RedisManager

        config = RedisStoreConfig.model_validate(store_config)

        redis = await self._container.get(RedisManager)

        return RedisStore(redis, config.connection, config.lock_connection)

    async def _create_locker(self, raw_locker_config: dict[str, Any] | None) -> Locker:
        from expanse.cache.asynchronous.locker import Locker

        if raw_locker_config is not None:
            locker_config = LockerConfig.model_validate(raw_locker_config)

            store_config = self._config.get(f"cache.stores.{locker_config.store}", None)
            if store_config is None:
                raise UnconfiguredStoreError(
                    f"Locker store '{locker_config.store}' is not configured."
                )

            if "driver" not in store_config:
                raise UnconfiguredStoreError(
                    f"Locker store '{locker_config.store}' is missing a driver configuration."
                )

            try:
                locker_store = await self._create_store(
                    locker_config.store, store_config
                )
            except UnsupportedStoreDriverError:
                raise UnsupportedStoreDriverError(
                    f"Locker store '{locker_config.store}' has an unsupported driver."
                )

            locker = Locker(locker_store)
        else:
            locker = Locker(await self._create_memory_store())

        return locker

    async def _create_bus(self, bus_config: dict[str, Any]) -> Bus:
        driver = bus_config.get("driver")

        if driver is None:
            raise UnconfiguredL1CacheBusError(
                "L1 cache bus configuration is missing a driver."
            )

        match driver:
            case "redis":
                from expanse.cache.asynchronous.buses.redis import RedisBus
                from expanse.cache.config.buses.redis import RedisBusConfig
                from expanse.redis.asynchronous.redis_manager import RedisManager

                config = RedisBusConfig.model_validate(bus_config)

                redis_manager = await self._container.get(RedisManager)

                return RedisBus(
                    redis_manager.connection(config.connection),
                    redis_manager.create_connection(config.connection),
                    config.channel,
                )

            case "memory":
                from expanse.cache.asynchronous.buses.memory import MemoryBus

                return MemoryBus()

            case _:
                raise UnsupportedL1CacheBusDriverError(
                    f"Unsupported L1 cache bus driver '{driver}'."
                )
