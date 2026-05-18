import pickle

from typing import Any
from typing import cast
from typing import override

from expanse.contracts.cache.asynchronous.store import Store
from expanse.redis.asynchronous.connections.connection import Connection


class RedisStore(Store):
    def __init__(self, connection: Connection) -> None:
        self._connection: Connection = connection

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
    async def get(self, key: str) -> Any | None:
        result = await self._connection.get(key)

        if result is None:
            return None

        return self._deserialize(result)

    @override
    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        results = await self._connection.mget(keys)

        return {
            key: self._deserialize(result) if result is not None else None
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
