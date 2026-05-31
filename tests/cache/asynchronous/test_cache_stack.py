from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

import pytest

from expanse.cache.asynchronous.buses.memory import MemoryBus
from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.cache_stack import CacheStack
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.contracts.cache.asynchronous.bus import Bus


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


_T = TypeVar("_T")


class NullBus(Bus):
    @property
    def id(self) -> str:
        return "null"

    async def publish(self, message: Any) -> None:
        pass

    def subscribe(
        self,
        message: type[_T],
        handler: Callable[[_T], None] | Callable[[_T], Awaitable[None]],
    ) -> None:
        pass

    async def close(self) -> None:
        pass


@pytest.fixture()
def l1_store() -> MemoryStore:
    return MemoryStore(SyncMemoryStore())


@pytest.fixture()
def l2_store() -> MemoryStore:
    return MemoryStore(SyncMemoryStore())


@pytest.fixture()
def l1_cache(l1_store: MemoryStore) -> Cache:
    return Cache("l1", l1_store)


@pytest.fixture()
def l2_cache(l2_store: MemoryStore) -> Cache:
    return Cache("l2", l2_store)


@pytest.fixture()
def stack(l1_store: MemoryStore, l2_store: MemoryStore) -> CacheStack:
    return CacheStack("test", l1_store, l2_store, NullBus())


# --- get ---


async def test_get_returns_l1_value_when_present(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("key", "l1_value")
    await l2_cache.set("key", "l2_value")

    assert await stack.get("key") == "l1_value"


async def test_get_returns_l2_value_on_l1_miss(
    stack: CacheStack, l2_cache: Cache
) -> None:
    await l2_cache.set("key", "l2_value")

    assert await stack.get("key") == "l2_value"


async def test_get_populates_l1_from_l2_on_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l2_cache.set("key", "value")

    await stack.get("key")

    assert await l1_cache.get("key") == "value"


async def test_get_returns_none_when_both_miss(stack: CacheStack) -> None:
    assert await stack.get("missing") is None


async def test_get_does_not_populate_l1_when_both_miss(
    stack: CacheStack, l1_cache: Cache
) -> None:
    await stack.get("missing")

    assert await l1_cache.get("missing") is None


# --- get_many ---


async def test_get_many_returns_all_l1_values_when_all_present(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("a", "l1_a")
    await l2_cache.set("a", "l2_a")

    result = await stack.get_many(["a"])

    assert result == {"a": "l1_a"}


async def test_get_many_fetches_missing_keys_from_l2(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("a", "l1_a")
    await l2_cache.set("b", "l2_b")

    result = await stack.get_many(["a", "b"])

    assert result["a"] == "l1_a"
    assert result["b"] == "l2_b"


async def test_get_many_populates_l1_for_l2_hits(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l2_cache.set("b", "l2_b")

    await stack.get_many(["b"])

    assert await l1_cache.get("b") == "l2_b"


async def test_get_many_returns_none_for_missing_keys(stack: CacheStack) -> None:
    result = await stack.get_many(["x", "y"])

    assert result == {"x": None, "y": None}


# --- set ---


async def test_set_writes_to_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await stack.set("key", "value")

    assert await l1_cache.get("key") == "value"
    assert await l2_cache.get("key") == "value"


async def test_set_returns_true(stack: CacheStack) -> None:
    assert await stack.set("key", "value") is True


# --- set_many ---


async def test_set_many_writes_to_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await stack.set_many({"a": 1, "b": 2})

    assert await l1_cache.get("a") == 1
    assert await l1_cache.get("b") == 2
    assert await l2_cache.get("a") == 1
    assert await l2_cache.get("b") == 2


async def test_set_many_returns_true(stack: CacheStack) -> None:
    assert await stack.set_many({"a": 1}) is True


# --- has ---


async def test_has_returns_true_when_key_in_l1(
    stack: CacheStack, l1_cache: Cache
) -> None:
    await l1_cache.set("key", "value")

    assert await stack.has("key") is True


async def test_has_returns_true_when_key_only_in_l2(
    stack: CacheStack, l2_cache: Cache
) -> None:
    await l2_cache.set("key", "value")

    assert await stack.has("key") is True


async def test_has_returns_false_when_key_in_neither(stack: CacheStack) -> None:
    assert await stack.has("missing") is False


# --- remember ---


async def test_remember_returns_l1_value_without_invoking_callback(
    stack: CacheStack, l1_cache: Cache
) -> None:
    await l1_cache.set("key", "cached")
    calls = 0

    def callback() -> str:
        nonlocal calls
        calls += 1
        return "computed"

    result = await stack.remember("key", callback)

    assert result == "cached"
    assert calls == 0


async def test_remember_executes_callback_and_populates_both_on_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    result = await stack.remember("key", lambda: "computed")

    assert result == "computed"
    assert await l1_cache.get("key") == "computed"
    assert await l2_cache.get("key") == "computed"


async def test_remember_populates_l1_from_l2_on_l1_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l2_cache.set("key", "l2_value")
    calls = 0

    def callback() -> str:
        nonlocal calls
        calls += 1
        return "computed"

    result = await stack.remember("key", callback)

    assert result == "l2_value"
    assert await l1_cache.get("key") == "l2_value"
    assert calls == 0


async def test_remember_supports_async_callback(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    async def async_callback() -> str:
        return "async_computed"

    result = await stack.remember("key", async_callback)

    assert result == "async_computed"
    assert await l1_cache.get("key") == "async_computed"
    assert await l2_cache.get("key") == "async_computed"


# --- delete ---


async def test_delete_removes_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("key", "value")
    await l2_cache.set("key", "value")

    await stack.delete("key")

    assert await l1_cache.get("key") is None
    assert await l2_cache.get("key") is None


async def test_delete_returns_true(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("key", "value")
    await l2_cache.set("key", "value")

    assert await stack.delete("key") is True


# --- delete_many ---


async def test_delete_many_removes_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set_many({"a": 1, "b": 2})
    await l2_cache.set_many({"a": 1, "b": 2})

    await stack.delete_many(["a", "b"])

    assert await l1_cache.get("a") is None
    assert await l1_cache.get("b") is None
    assert await l2_cache.get("a") is None
    assert await l2_cache.get("b") is None


async def test_delete_many_returns_true(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set_many({"a": 1})
    await l2_cache.set_many({"a": 1})

    assert await stack.delete_many(["a"]) is True


# --- clear ---


async def test_clear_removes_all_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set_many({"a": 1, "b": 2})
    await l2_cache.set_many({"c": 3, "d": 4})

    await stack.clear()

    assert await l1_cache.get("a") is None
    assert await l1_cache.get("b") is None
    assert await l2_cache.get("c") is None
    assert await l2_cache.get("d") is None


async def test_clear_returns_true(stack: CacheStack) -> None:
    assert await stack.clear() is True


# --- pop ---


async def test_pop_returns_l1_value_and_removes_from_both(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    await l1_cache.set("key", "l1_value")
    await l2_cache.set("key", "l2_value")

    result = await stack.pop("key")

    assert result == "l1_value"
    assert await l1_cache.get("key") is None
    assert await l2_cache.get("key") is None


async def test_pop_returns_l2_value_and_removes_it_on_l1_miss(
    stack: CacheStack, l2_cache: Cache
) -> None:
    await l2_cache.set("key", "l2_value")

    result = await stack.pop("key")

    assert result == "l2_value"
    assert await l2_cache.get("key") is None


async def test_pop_returns_none_when_both_miss(stack: CacheStack) -> None:
    assert await stack.pop("missing") is None


# --- lock ---


async def test_lock_delegates_to_l2_store(stack: CacheStack, l2_cache: Cache) -> None:
    stack_lock = stack.lock("my-lock")
    l2_lock = l2_cache.lock("my-lock")

    assert type(stack_lock) is type(l2_lock)


# --- bus invalidation ---


async def test_bus_invalidates_l1_on_set_from_another_stack(
    l1_store: MemoryStore, l2_store: MemoryStore, l1_cache: Cache
) -> None:
    bus = MemoryBus()
    # Both stacks share the same L2; each has its own L1
    _stack_a = CacheStack("a", l1_store, l2_store, bus)
    stack_b = CacheStack("b", MemoryStore(SyncMemoryStore()), l2_store, bus)

    await l1_cache.set("key", "stale")

    await stack_b.set("key", "new_value")

    assert await l1_cache.get("key") is None


async def test_bus_invalidates_l1_on_delete_from_another_stack(
    l1_store: MemoryStore, l2_store: MemoryStore, l1_cache: Cache
) -> None:
    bus = MemoryBus()
    # Both stacks share the same L2; each has its own L1
    _stack_a = CacheStack("a", l1_store, l2_store, bus)
    stack_b = CacheStack("b", MemoryStore(SyncMemoryStore()), l2_store, bus)

    await l1_cache.set("key", "value")
    await l2_store.set("key", "value")

    await stack_b.delete("key")

    assert await l1_cache.get("key") is None


async def test_bus_clears_l1_on_clear_from_another_stack(
    l1_store: MemoryStore, l2_store: MemoryStore, l1_cache: Cache
) -> None:
    bus = MemoryBus()
    # Both stacks share the same L2; each has its own L1
    _stack_a = CacheStack("a", l1_store, l2_store, bus)
    stack_b = CacheStack("b", MemoryStore(SyncMemoryStore()), l2_store, bus)

    await l1_cache.set("key", "value")

    await stack_b.clear()

    assert await l1_cache.get("key") is None
