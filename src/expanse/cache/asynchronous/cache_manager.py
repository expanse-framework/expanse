from typing import Any
from typing import cast

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.config.locker import LockerConfig
from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.cache.asynchronous.store import Store
from expanse.core.application import Application


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

        store = await self._create_store(name)

        from expanse.cache.asynchronous.locker import Locker

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
            locker = Locker(self._create_memory_store())

        self._caches[name] = Cache(store, locker=locker)

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
