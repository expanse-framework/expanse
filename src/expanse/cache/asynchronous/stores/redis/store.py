import pickle

from typing import TYPE_CHECKING
from typing import Any
from typing import cast
from typing import override

from expanse.contracts.cache.asynchronous.store import Store
from expanse.contracts.cache.cache_item import CacheItem
from expanse.redis.asynchronous.redis_manager import RedisManager


if TYPE_CHECKING:
    from expanse.cache.asynchronous.locks.redis_lock import RedisLock


class RedisStore(Store):
    def __init__(
        self,
        redis: RedisManager,
        connection_name: str | None = None,
        lock_connection_name: str | None = None,
    ) -> None:
        self._redis: RedisManager = redis
        self._connection_name: str | None = connection_name
        self._lock_connection_name: str | None = lock_connection_name

    @property
    def _connection(self):
        return self._redis.connection(self._connection_name)

    @property
    def _lock_connection(self):
        return self._redis.connection(
            self._lock_connection_name or self._connection_name
        )

    def _serialize(self, value: Any) -> str:
        return pickle.dumps(value).hex()

    def _deserialize(self, data: str) -> Any:
        return pickle.loads(bytes.fromhex(data))

    @override
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return cast(
            "bool", await self._connection.set(key, self._serialize(value), ex=ttl)
        )

    @override
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        async with self._connection.pipeline() as pipeline:
            for key, value in items.items():
                pipeline.set(key, self._serialize(value), ex=ttl)

            results = await pipeline.execute()

            return all(cast("bool", result) for result in results)

    @override
    async def get(self, key: str) -> CacheItem:
        result = await self._connection.get(key)

        if result is None:
            return CacheItem(key=key)

        return CacheItem(key=key, value=self._deserialize(result), is_hit=True)

    @override
    async def get_many(self, keys: list[str]) -> dict[str, CacheItem]:
        results = await self._connection.mget(keys)

        return {
            key: (
                CacheItem(key=key, value=self._deserialize(result), is_hit=True)
                if result is not None
                else CacheItem(key=key)
            )
            for key, result in zip(keys, results)
        }

    @override
    async def has(self, key: str) -> bool:
        return await self._connection.exists(key) > 0

    @override
    async def delete(self, key: str) -> bool:
        return await self._connection.delete(key) > 0

    @override
    async def clear(self) -> bool:
        await self._connection.flushdb()

        return True

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "RedisLock":
        from expanse.cache.asynchronous.locks.redis_lock import RedisLock

        return RedisLock(self._lock_connection, name, ttl, owner=owner, refresh=refresh)
