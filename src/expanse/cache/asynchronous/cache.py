import inspect
import logging

from collections.abc import Awaitable
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast
from typing import overload
from typing import override

from expanse.cache.logger import Logger
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.cache.asynchronous.locker import Locker
from expanse.contracts.cache.asynchronous.store import Store
from expanse.support._concurrency import run_in_threadpool
from expanse.support._concurrency import should_run_in_threadpool


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock

_T = TypeVar("_T")

logger = cast("Logger", logging.getLogger(__name__))
logger.__class__ = Logger


class Cache(CacheContract):
    def __init__(self, name: str, store: Store, locker: Locker | None = None) -> None:
        self._name: str = name
        self._store: Store = store
        self._locker: Locker | None = locker

    @override
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store an item in the cache.

        :param key: The key under which the value should be stored.
        :param value: The value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.
        :param until: The datetime until which the cache item should be valid.

        :return: True if the item was successfully stored, False otherwise.
        """
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        if ttl is not None and ttl <= 0:
            return await self.delete(key)

        return await self._store.set(key, value, ttl)

    @override
    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store multiple items in the cache.

        :param items: A dictionary of key-value pairs to be stored.
        :param ttl: The time-to-live (TTL) for the cache items in seconds.
        :param until: The datetime until which the cache items should be valid.

        :return: True if the items were successfully stored, False otherwise.
        """
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        if ttl is not None and ttl <= 0:
            return await self.delete_many(list(items.keys()))

        return await self._store.set_many(items, ttl)

    @overload
    async def get(self, key: str) -> Any | None: ...

    @overload
    async def get(self, key: str, default: Any) -> Any: ...

    @override
    async def get(self, key: str, default: Any | None = None) -> Any | None:
        """
        Retrieve an item from the cache.

        :param key: The key of the item to retrieve.
        :param default: The value to return if the key does not exist in the cache.

        :return: The value associated with the key, or the default value if the key does not exist.
        """
        item = await self._store.get(key)

        if not item.is_hit:
            logger.miss(self._name, key)

            return default

        logger.hit(self._name, key)

        return item.value

    @override
    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        """
        Retrieve multiple items from the cache.

        :param keys: A list of keys to retrieve.
        :param default: The value to return for keys that do not exist in the cache.

        :return: A dictionary mapping each key to its associated value, or the default value if the key does not exist.
        """
        defaults = keys if isinstance(keys, dict) else {}
        if isinstance(keys, dict):
            keys = list(keys.keys())

        items = await self._store.get_many(keys)

        return {
            key: item.value if item.is_hit else defaults.get(key)
            for key, item in items.items()
        }

    @overload
    async def remember(
        self,
        key: str,
        callback: Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T: ...

    @overload
    async def remember(
        self,
        key: str,
        callback: Callable[..., _T],
        ttl: int | None = None,
    ) -> _T: ...

    @override
    async def remember(
        self,
        key: str,
        callback: Callable[..., _T] | Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T:
        """
        Store the result of a callback in the cache if the key does not already exist.

        If a locker is configured for the cache, this method will acquire a lock for the key before checking
        if it exists in the cache and executing the callback.
        This ensures that only one process can execute the callback and store
        the result in the cache for a given key at a time, avoiding cache stampedes.

        :param key: The key under which the value should be stored.
        :param callback: The callback to generate the value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.

        :return: The value returned by the callback, either from the cache or freshly generated.
        """
        if self._locker is not None:
            lock = self._locker.lock(
                f"remember:{key}",
                # We force a TTL on the lock to prevent deadlocks in case the process that acquired the lock
                # crashes before releasing it.
                ttl=30,
            )
            logger.debug("Attempting to acquire remember lock", extra={"key": key})

            async with lock:
                return await self._compute(key, callback, ttl)

        return await self._compute(key, callback, ttl)

    @override
    async def has(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        :param key: The key to check for existence.

        :return: True if the key exists in the cache, False otherwise.
        """
        return await self._store.has(key)

    @override
    async def pop(self, key: str) -> Any | None:
        """
        Remove an item from the cache and return its value.

        :param key: The key of the item to remove.

        :return: The value associated with the key, or None if the key does not exist.
        """
        item = await self._store.get(key)

        if item.is_hit:
            await self.delete(key)
            return item.value

        return None

    @override
    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        :param key: The key to delete.

        :return: True if the key was successfully deleted, False otherwise.
        """
        result = await self._store.delete(key)
        if result:
            logger.delete(self._name, key)

        return result

    @override
    async def delete_many(self, keys: list[str]) -> bool:
        """
        Delete multiple keys from the cache.

        :param keys: The keys to delete.

        :return: True if all keys were successfully deleted, False otherwise.
        """
        deleted_keys = []
        for key in keys:
            if await self.delete(key):
                deleted_keys.append(key)

        if deleted_keys:
            logger.delete(self._name, ", ".join(deleted_keys))

        return len(deleted_keys) == len(keys)

    @override
    async def clear(self) -> bool:
        """
        Clear all items from the cache.
        """
        result = await self._store.clear()
        if result:
            logger.clear(self._name)

        return result

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "Lock":
        """
        Get a lock for the cache.

        :param name: The name of the lock.
        :param ttl: The time-to-live (TTL) for the lock in seconds.
        :param owner: The owner of the lock. If None, the lock will be owned by the current process.
        :param refresh: Whether to automatically refresh the lock before it expires.

        :return: A Lock instance for the specified name.
        """
        return self._store.lock(name, ttl, owner, refresh)

    async def _compute(
        self,
        key: str,
        callback: Callable[..., _T] | Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T:
        """
        Compute the value for a given key using a callback and store it in the cache.

        :param key: The key under which the value should be stored.
        :param callback: The callback to generate the value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.

        :return: The value returned by the callback.
        """
        cached = await self._store.get(key)
        if cached.is_hit:
            return cast("_T", cached.value)

        logger.debug(
            "Computing cache value", extra={"key": key, "callback": callback.__name__}
        )
        value: _T
        if inspect.iscoroutinefunction(callback):
            value = await cast("Callable[..., Awaitable[_T]]", callback)()
        elif not should_run_in_threadpool(callback):
            value = cast("Callable[..., _T]", callback)()
        else:
            value = await run_in_threadpool(cast("Callable[..., _T]", callback))

        logger.debug(
            "Computed cache value", extra={"key": key, "callback": callback.__name__}
        )
        await self._store.set(key, value, ttl)

        return value
