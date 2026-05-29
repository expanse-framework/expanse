import logging

from collections.abc import Awaitable
from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.cache.messages.cache_item_set import CacheItemSet
from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock


_T = TypeVar("_T")


logger = logging.getLogger(__name__)


class CacheStack(CacheContract):
    def __init__(
        self, l1_cache: CacheContract, l2_cache: CacheContract, bus: Bus
    ) -> None:
        self._l1_cache: CacheContract = l1_cache
        self._l2_cache: CacheContract = l2_cache
        self._bus: Bus = bus
        self._bus.subscribe(self._on_cache_item_set)

    @override
    async def get(self, key: str, default: Any | None = None) -> Any | None:
        value = await self._l1_cache.get(key)

        if value is not None:
            logger.debug("L1 cache hit for key: %s", key)

            return value

        value = await self._l2_cache.get(key)

        if value is not None:
            await self._l1_cache.set(key, value)

            logger.debug("L2 cache hit for key: %s", key)

        return value

    @override
    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        l1_values = await self._l1_cache.get_many(keys)

        missing_keys = [key for key in keys if l1_values.get(key) is None]

        if not missing_keys:
            logger.debug("L1 cache hit for keys: %s", missing_keys)

            return l1_values

        l2_values = await self._l2_cache.get_many(missing_keys)

        for key, value in l2_values.items():
            if value is not None:
                await self._l1_cache.set(key, value)

        logger.debug("L2 cache hit for keys: %s", missing_keys)

        return {**l1_values, **l2_values}

    @override
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: Any | None = None,
    ) -> bool:
        await self._l1_cache.set(key, value, ttl, until)

        l2_result = await self._l2_cache.set(key, value, ttl, until)

        if l2_result:
            await self._bus.publish(CacheItemSet(key))
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
        await self._l1_cache.set_many(items, ttl, until)

        l2_result = await self._l2_cache.set_many(items, ttl, until)

        if l2_result:
            # TODO: Dispatch message to bus to invalidate L1 cache in other instances
            pass

        return True

    @override
    async def has(self, key: str) -> bool:
        if await self._l1_cache.has(key):
            return True

        return await self._l2_cache.has(key)

    @override
    async def remember(
        self,
        key: str,
        callback: Callable[..., _T] | Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T:
        # If the value is in the L1 cache, return it immediately
        value = await self._l1_cache.get(key)

        if value is not None:
            return value

        value = await self._l2_cache.remember(key, callback, ttl)

        await self._l1_cache.set(key, value, ttl)

        # TODO: Dispatch message to bus to invalidate L1 cache in other instances

        return value

    @override
    async def delete(self, key: str) -> bool:
        await self._l1_cache.delete(key)

        l2_result = await self._l2_cache.delete(key)

        if l2_result:
            # TODO: Dispatch message to bus to invalidate L1 cache in other instances
            pass
        else:
            logger.warning("Failed to delete key '%s' in L2 cache.", key)

        return True

    @override
    async def delete_many(self, keys: list[str]) -> bool:
        await self._l1_cache.delete_many(keys)

        l2_result = await self._l2_cache.delete_many(keys)

        if l2_result:
            # TODO: Dispatch message to bus to invalidate L1 cache in other instances
            pass
        else:
            logger.warning("Failed to delete keys '%s' in L2 cache.", keys)

        return True

    @override
    async def clear(self) -> bool:
        await self._l1_cache.clear()

        l2_result = await self._l2_cache.clear()

        if l2_result:
            # TODO: Dispatch message to bus to invalidate L1 cache in other instances
            pass
        else:
            logger.warning("Failed to clear L2 cache.")

        return True

    @override
    async def pop(self, key: str) -> Any | None:
        value = await self._l1_cache.pop(key)

        if value is not None:
            if await self._l2_cache.delete(key):
                # TODO: Dispatch message to bus to invalidate L1 cache in other instances
                pass

            return value

        value = await self._l2_cache.pop(key)

        if value is not None:
            return value

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "Lock":
        return self._l2_cache.lock(name, ttl, owner, refresh)

    async def _on_cache_item_set(self, message: CacheItemSet) -> None:
        logger.debug("Received cache item set message for key %s", message.key)
        await self._l1_cache.delete(message.key)

        await self.get(message.key)
