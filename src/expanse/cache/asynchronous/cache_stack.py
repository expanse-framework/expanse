import inspect
import time

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

from expanse.cache.logger import get_logger
from expanse.cache.messages.cache_clear import CacheClear
from expanse.cache.messages.cache_item_deleted import CacheItemDeleted
from expanse.cache.messages.cache_item_set import CacheItemSet
from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.contracts.cache.asynchronous.store import Store as StoreContract
from expanse.support._concurrency import run_in_threadpool
from expanse.support._concurrency import should_run_in_threadpool


if TYPE_CHECKING:
    from expanse.contracts.cache.asynchronous.locker import Locker
    from expanse.contracts.lock.asynchronous.lock import Lock


_T = TypeVar("_T")


logger = get_logger(__name__)


class CacheStack(CacheContract):
    def __init__(
        self,
        name: str,
        l1_store: StoreContract,
        l2_store: StoreContract,
        bus: Bus,
        locker: "Locker | None" = None,
    ) -> None:
        self._name: str = name
        self._l1_store: StoreContract = l1_store
        self._l2_store: StoreContract = l2_store
        self._bus: Bus = bus
        self._bus.subscribe(CacheItemSet, self._on_cache_item_set)
        self._bus.subscribe(CacheItemDeleted, self._on_cache_item_deleted)
        self._bus.subscribe(CacheClear, self._on_cache_clear)
        self._locker: Locker | None = locker

    @override
    async def get(self, key: str, default: Any | None = None) -> Any:
        item = await self._l1_store.get(key)

        if item.is_hit:
            logger.l1_hit(self._name, key)

            return item.value

        item = await self._l2_store.get(key)

        if item.is_hit:
            ttl = None
            if item.expiration is not None:
                ttl = int(time.time()) - item.expiration

            await self._l1_store.set(key, item.value, ttl)

            logger.l2_hit(self._name, key)

        return item.value

    @override
    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any]:
        defaults = keys if isinstance(keys, dict) else {}
        if isinstance(keys, dict):
            keys = list(keys.keys())

        l1_items = await self._l1_store.get_many(keys)

        missing_keys = [key for key in keys if not l1_items[key].is_hit]

        if not missing_keys:
            logger.l1_hit(self._name, ", ".join(keys))

            return {key: l1_items[key].value for key in keys}

        l2_items = await self._l2_store.get_many(missing_keys)

        for key, item in l2_items.items():
            if item.is_hit:
                await self._l1_store.set(key, item.value)

        logger.l2_hit(self._name, ", ".join(missing_keys))

        return {
            key: l1_items[key].value
            if l1_items[key].is_hit
            else l2_items[key].value
            if l2_items[key].is_hit
            else defaults.get(key)
            for key in keys
        }

    @override
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: Any | None = None,
    ) -> bool:
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        await self._l1_store.set(key, value, ttl)

        l2_result = await self._l2_store.set(key, value, ttl)

        if l2_result:
            await self._bus.publish(CacheItemSet([key]))
        else:
            logger.warning("Failed to set key '%s' in L2 cache.", key)

        return True

    @override
    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: Any | None = None,
    ) -> bool:
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        await self._l1_store.set_many(items, ttl)

        l2_result = await self._l2_store.set_many(items, ttl)

        if l2_result:
            await self._bus.publish(CacheItemSet(list(items.keys())))

        return True

    @override
    async def has(self, key: str) -> bool:
        if await self._l1_store.has(key):
            return True

        return await self._l2_store.has(key)

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
        # Check th L1 cache first
        item = await self._l1_store.get(key)
        if item.is_hit:
            return cast("_T", item.value)

        if self._locker is not None:
            lock = self._locker.lock(
                f"remember:{key}",
                # We force a TTL on the lock to prevent deadlocks in case the process that acquired the lock
                # crashes before releasing it.
                ttl=30,
            )
            logger.debug(
                "Attempting to acquire lock for remember operation", extra={"key": key}
            )

            async with lock:
                return await self._compute(key, callback, ttl)

        return await self._compute(key, callback, ttl)

    @override
    async def delete(self, key: str) -> bool:
        await self._l1_store.delete(key)

        l2_result = await self._l2_store.delete(key)

        if l2_result:
            await self._bus.publish(CacheItemDeleted([key]))
        else:
            logger.warning("Failed to delete key in L2 cache.", extra={"key": key})

        return True

    @override
    async def delete_many(self, keys: list[str]) -> bool:
        for key in keys:
            await self._l1_store.delete(key)

        l2_results = [await self._l2_store.delete(key) for key in keys]

        if all(l2_results):
            await self._bus.publish(CacheItemDeleted(keys))
        else:
            logger.warning("Failed to delete keys in L2 cache.", extra={"keys": keys})

        return True

    @override
    async def clear(self) -> bool:
        await self._l1_store.clear()

        l2_result = await self._l2_store.clear()

        if l2_result:
            await self._bus.publish(CacheClear())
        else:
            logger.warning("Failed to clear L2 cache.")

        return True

    @override
    async def pop(self, key: str) -> Any:
        value = await self._l1_store.get(key)

        if value.is_hit:
            await self.delete(key)
            return value.value

        value = await self._l2_store.get(key)

        if value.is_hit:
            await self.delete(key)
            return value.value

        return None

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "Lock":
        return self._l2_store.lock(name, ttl, owner, refresh)

    async def _on_cache_item_set(self, message: CacheItemSet) -> None:
        logger.debug(
            "Invalidating cache items",
            extra={"keys": message.keys, "source": CacheItemSet.__name__},
        )

        for key in message.keys:
            await self._l1_store.delete(key)

    async def _on_cache_item_deleted(self, message: CacheItemDeleted) -> None:
        logger.debug(
            "Deleting cache items",
            extra={"keys": message.keys, "source": CacheItemDeleted.__name__},
        )

        for key in message.keys:
            await self._l1_store.delete(key)

    async def _on_cache_clear(self, message: CacheClear) -> None:
        logger.debug(
            "Clearing cache",
            extra={"source": CacheClear.__name__},
        )

        await self._l1_store.clear()

    async def _compute(
        self,
        key: str,
        callback: Callable[..., _T] | Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T:
        item = await self._l2_store.get(key)
        if item.is_hit:
            item_ttl = None
            if item.expiration is not None:
                item_ttl = int(time.time()) - item.expiration
            await self._l1_store.set(key, item.value, item_ttl)

            return cast("_T", item.value)

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
        await self.set(key, value, ttl)

        return value
