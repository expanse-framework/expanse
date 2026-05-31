import logging

from typing import Any

from expanse.cache.config.locker import LockerConfig
from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.cache.synchronous.cache import Cache
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.synchronous.bus import Bus
from expanse.contracts.cache.synchronous.cache import Cache as CacheContract
from expanse.contracts.cache.synchronous.store import Store
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

        self._caches[name] = await self._create_cache(name)

        return self._caches[name]

    def get_default_store_name(self) -> str:
        default_store: str | None = self._config.get("cache.store")
        if default_store is None:
            raise NoDefaultStoreError("No default cache store configured.")

        return default_store

    async def _create_cache(self, name: str) -> CacheContract:
        store = await self._create_store(name)

        from expanse.cache.synchronous.locker import Locker

        raw_locker_config = self._config.get("cache.locker", None)
        if raw_locker_config is not None:
            locker_config = LockerConfig.model_validate(raw_locker_config)

            try:
                locker_store = await self._create_store(locker_config.store)
            except UnconfiguredStoreError:
                raise UnconfiguredStoreError(
                    f"Locker store '{locker_config.store}' is not configured."
                )
            except UnsupportedStoreDriverError:
                raise UnsupportedStoreDriverError(
                    f"Locker store '{locker_config.store}' has an unsupported driver."
                )

            locker = Locker(locker_store)
        else:
            locker = Locker(
                self._create_memory_store(
                    {
                        "driver": "memory",
                        "max_items": 1000,
                    }
                )
            )

        stores: dict[str, dict[str, Any]] = self._config.get("cache.stores", {})
        store_config = stores[name]
        l1_cache_config = store_config.get("l1_cache", None)

        if not l1_cache_config:
            logger.debug(
                "Creating single-level cache for store '%s' with driver '%s'.",
                name,
                store_config["driver"],
            )
            return Cache(name, store, locker=locker)

        l1_store_config = l1_cache_config.get("store", None)
        if not l1_store_config:
            raise UnconfiguredStoreError(
                f"L1 cache configuration for store '{name}' is missing a store configuration."
            )

        l1_store = self._create_l1_store(l1_store_config)

        l1_bus_config = l1_cache_config.get("bus", None)
        if not l1_bus_config:
            l1_bus_config = {"driver": "memory"}

        bus = await self._create_bus(l1_bus_config)

        logger.debug(
            "Creating two-level cache for store '%s' with driver '%s' and L1 cache driver '%s'.",
            name,
            store_config["driver"],
            l1_store_config["driver"],
        )

        from expanse.cache.synchronous.cache_stack import CacheStack

        return CacheStack(name, l1_store, store, bus, locker=locker)

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
                return self._create_memory_store(store_config)

            case "database":
                return await self._create_database_store(store_config)

            case "file":
                return self._create_file_store(store_config)

            case "redis":
                return await self._create_redis_store(store_config)

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported cache store driver '{store_config['driver']}' for store '{name}'."
                )

    def _create_l1_store(self, l1_cache_config: dict[str, Any]) -> Store:
        if "driver" not in l1_cache_config:
            raise UnconfiguredStoreError("L1 cache configuration is missing a driver.")

        match l1_cache_config["driver"]:
            case "memory":
                return self._create_memory_store(l1_cache_config)

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported L1 cache store driver '{l1_cache_config['driver']}'."
                )

    def _create_memory_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.config.memory import MemoryStoreConfig
        from expanse.cache.synchronous.stores.memory import MemoryStore

        config = MemoryStoreConfig.model_validate(store_config)

        return MemoryStore(
            max_items=config.max_items,
            max_size=config.max_size,
            default_ttl=config.default_ttl,
        )

    async def _create_database_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.config.database import DatabaseStoreConfig
        from expanse.cache.synchronous.stores.database.store import DatabaseStore
        from expanse.database.synchronous.database_manager import DatabaseManager

        db = await self._container.get(DatabaseManager)

        config = DatabaseStoreConfig.model_validate(store_config)

        return DatabaseStore(config, db)

    def _create_file_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.config.file import FileStoreConfig
        from expanse.cache.synchronous.stores.file.store import FileStore

        config = FileStoreConfig.model_validate(store_config)

        path = config.path
        if not path.is_absolute():
            path = self._app.base_path.joinpath(path)

        locks_path = config.locks_path
        if locks_path is not None and not locks_path.is_absolute():
            locks_path = self._app.base_path.joinpath(locks_path)

        return FileStore(path, config.permissions, locks_path=locks_path)

    async def _create_redis_store(self, store_config: dict[str, Any]) -> Store:
        from expanse.cache.config.redis import RedisStoreConfig
        from expanse.cache.synchronous.stores.redis.store import RedisStore
        from expanse.redis.synchronous.redis_manager import RedisManager

        config = RedisStoreConfig.model_validate(store_config)

        redis = await self._container.get(RedisManager)

        return RedisStore(redis, config.connection, config.lock_connection)

    async def _create_bus(self, bus_config: dict[str, Any]) -> Bus:
        driver = bus_config.get("driver")

        match driver:
            case "redis":
                from expanse.cache.config.buses.redis import RedisBusConfig
                from expanse.cache.synchronous.buses.redis import RedisBus
                from expanse.redis.synchronous.redis_manager import RedisManager

                config = RedisBusConfig.model_validate(bus_config)

                redis = await self._container.get(RedisManager)

                return RedisBus(
                    redis.connection(config.connection),
                    redis.create_connection(config.connection),
                    config.channel,
                )

            case "memory":
                from expanse.cache.synchronous.buses.memory import MemoryBus

                return MemoryBus()

            case _:
                raise UnsupportedStoreDriverError(
                    f"Unsupported L1 cache bus driver '{driver}'."
                )
