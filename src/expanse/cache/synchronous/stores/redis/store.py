import pickle

from typing import Any
from typing import cast
from typing import override

from expanse.contracts.cache.synchronous.store import Store
from expanse.redis.synchronous.connections.connection import Connection


class RedisStore(Store):
    def __init__(self, connection: Connection) -> None:
        self._connection: Connection = connection

    def _serialize(self, value: Any) -> str:
        return pickle.dumps(value).hex()

    def _deserialize(self, data: str) -> Any:
        return pickle.loads(bytes.fromhex(data))

    @override
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return cast("bool", self._connection.set(key, self._serialize(value), ex=ttl))

    @override
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        with self._connection.pipeline() as pipeline:
            for key, value in items.items():
                pipeline.set(key, self._serialize(value), ex=ttl)

            results = pipeline.execute()

            return all(cast("bool", result) for result in results)

    @override
    def get(self, key: str) -> Any | None:
        result = self._connection.get(key)

        if result is None:
            return None

        return self._deserialize(result)

    @override
    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        results = self._connection.mget(keys)

        return {
            key: self._deserialize(result) if result is not None else None
            for key, result in zip(keys, results)
        }

    @override
    def has(self, key: str) -> bool:
        return self._connection.exists(key) > 0

    @override
    def delete(self, key: str) -> bool:
        return self._connection.delete(key) > 0

    @override
    def clear(self) -> bool:
        self._connection.flushdb()

        return True
