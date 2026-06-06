from __future__ import annotations

import logging
import time

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import cast
from typing import override

from expanse.cache.messages.cache_clear import CacheClear
from expanse.cache.messages.cache_item_deleted import CacheItemDeleted
from expanse.cache.messages.cache_item_set import CacheItemSet
from expanse.contracts.cache.synchronous.cache import Cache as CacheContract


if TYPE_CHECKING:
    from collections.abc import Callable

    from expanse.contracts.cache.synchronous.bus import Bus
    from expanse.contracts.cache.synchronous.locker import Locker
    from expanse.contracts.cache.synchronous.store import Store as StoreContract
    from expanse.contracts.lock.synchronous.lock import Lock


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class CacheStack(CacheContract):
    def __init__(
        self,
        name: str,
        l1_store: StoreContract,
        l2_store: StoreContract,
        bus: Bus,
        locker: Locker | None = None,
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
    def get(self, key: str, default: Any | None = None) -> Any | None:
        item = self._l1_store.get(key)

        if item.is_hit:
            return item.value

        item = self._l2_store.get(key)

        if item.is_hit:
            ttl = None
            if item.expiration is not None:
                ttl = int(time.time()) - item.expiration

            self._l1_store.set(key, item.value, ttl)

        return item.value

    @override
    def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any]:
        defaults = keys if isinstance(keys, dict) else {}
        if isinstance(keys, dict):
            keys = list(keys.keys())

        l1_items = self._l1_store.get_many(keys)

        missing_keys = [key for key in keys if not l1_items[key].is_hit]

        if not missing_keys:
            return {key: l1_items[key].value for key in keys}

        l2_items = self._l2_store.get_many(missing_keys)

        for key, item in l2_items.items():
            if item.is_hit:
                self._l1_store.set(key, item.value)

        return {
            key: l1_items[key].value
            if l1_items[key].is_hit
            else l2_items[key].value
            if l2_items[key].is_hit
            else defaults.get(key)
            for key in keys
        }

    @override
    def set(
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

        self._l1_store.set(key, value, ttl)

        l2_result = self._l2_store.set(key, value, ttl)

        if l2_result:
            self._bus.publish(CacheItemSet([key]))
        else:
            logger.warning("Failed to set key '%s' in L2 cache.", key)

        return True

    @override
    def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: Any | None = None,
    ) -> bool:
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        self._l1_store.set_many(items, ttl)

        l2_result = self._l2_store.set_many(items, ttl)

        if l2_result:
            self._bus.publish(CacheItemSet(list(items.keys())))

        return True

    @override
    def has(self, key: str) -> bool:
        if self._l1_store.has(key):
            return True

        return self._l2_store.has(key)

    @override
    def remember(
        self,
        key: str,
        callback: Callable[..., _T],
        ttl: int | None = None,
    ) -> _T:
        item = self._l1_store.get(key)
        if item.is_hit:
            return cast("_T", item.value)

        if self._locker is not None:
            lock = self._locker.lock(f"remember:{key}", ttl=30)

            with lock:
                return self._compute(key, callback, ttl)

        return self._compute(key, callback, ttl)

    @override
    def delete(self, key: str) -> bool:
        self._l1_store.delete(key)

        l2_result = self._l2_store.delete(key)

        if l2_result:
            self._bus.publish(CacheItemDeleted([key]))
        else:
            logger.warning("Failed to delete key in L2 cache.", extra={"key": key})

        return True

    @override
    def delete_many(self, keys: list[str]) -> bool:
        for key in keys:
            self._l1_store.delete(key)

        l2_results = [self._l2_store.delete(key) for key in keys]

        if all(l2_results):
            self._bus.publish(CacheItemDeleted(keys))
        else:
            logger.warning("Failed to delete keys in L2 cache.", extra={"keys": keys})

        return True

    @override
    def clear(self) -> bool:
        self._l1_store.clear()

        l2_result = self._l2_store.clear()

        if l2_result:
            self._bus.publish(CacheClear())
        else:
            logger.warning("Failed to clear L2 cache.")

        return True

    @override
    def pop(self, key: str) -> Any | None:
        value = self._l1_store.get(key)

        if value.is_hit:
            self.delete(key)
            return value.value

        value = self._l2_store.get(key)

        if value.is_hit:
            self.delete(key)
            return value.value

        return None

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> Lock:
        return self._l2_store.lock(name, ttl, owner, refresh)

    def _on_cache_item_set(self, message: CacheItemSet) -> None:
        for key in message.keys:
            self._l1_store.delete(key)

    def _on_cache_item_deleted(self, message: CacheItemDeleted) -> None:
        for key in message.keys:
            self._l1_store.delete(key)

    def _on_cache_clear(self, message: CacheClear) -> None:
        self._l1_store.clear()

    def _compute(
        self,
        key: str,
        callback: Callable[..., _T],
        ttl: int | None = None,
    ) -> _T:
        item = self._l2_store.get(key)
        if item.is_hit:
            item_ttl = None
            if item.expiration is not None:
                item_ttl = int(time.time()) - item.expiration
            self._l1_store.set(key, item.value, item_ttl)

            return cast("_T", item.value)

        value: _T = callback()

        self.set(key, value, ttl)

        return value
