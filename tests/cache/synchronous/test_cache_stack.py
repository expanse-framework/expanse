from __future__ import annotations

import pytest

from expanse.cache.synchronous.cache import Cache
from expanse.cache.synchronous.cache_stack import CacheStack
from expanse.cache.synchronous.stores.memory import MemoryStore


@pytest.fixture()
def l1_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture()
def l2_store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture()
def l1_cache(l1_store: MemoryStore) -> Cache:
    return Cache(l1_store)


@pytest.fixture()
def l2_cache(l2_store: MemoryStore) -> Cache:
    return Cache(l2_store)


@pytest.fixture()
def stack(l1_cache: Cache, l2_cache: Cache) -> CacheStack:
    return CacheStack(l1_cache, l2_cache)


# --- get ---


async def test_get_returns_l1_value_when_present(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("key", "l1_value")
    l2_cache.set("key", "l2_value")

    assert stack.get("key") == "l1_value"


async def test_get_returns_l2_value_on_l1_miss(
    stack: CacheStack, l2_cache: Cache
) -> None:
    l2_cache.set("key", "l2_value")

    assert stack.get("key") == "l2_value"


async def test_get_populates_l1_from_l2_on_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l2_cache.set("key", "value")

    stack.get("key")

    assert l1_cache.get("key") == "value"


async def test_get_returns_none_when_both_miss(stack: CacheStack) -> None:
    assert stack.get("missing") is None


async def test_get_does_not_populate_l1_when_both_miss(
    stack: CacheStack, l1_cache: Cache
) -> None:
    stack.get("missing")

    assert l1_cache.get("missing") is None


# --- get_many ---


async def test_get_many_returns_all_l1_values_when_all_present(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("a", "l1_a")
    l2_cache.set("a", "l2_a")

    result = stack.get_many(["a"])

    assert result == {"a": "l1_a"}


async def test_get_many_fetches_missing_keys_from_l2(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("a", "l1_a")
    l2_cache.set("b", "l2_b")

    result = stack.get_many(["a", "b"])

    assert result["a"] == "l1_a"
    assert result["b"] == "l2_b"


async def test_get_many_populates_l1_for_l2_hits(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l2_cache.set("b", "l2_b")

    stack.get_many(["b"])

    assert l1_cache.get("b") == "l2_b"


async def test_get_many_returns_none_for_missing_keys(stack: CacheStack) -> None:
    result = stack.get_many(["x", "y"])

    assert result == {"x": None, "y": None}


# --- set ---


async def test_set_writes_to_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    stack.set("key", "value")

    assert l1_cache.get("key") == "value"
    assert l2_cache.get("key") == "value"


async def test_set_returns_true(stack: CacheStack) -> None:
    assert stack.set("key", "value") is True


# --- set_many ---


async def test_set_many_writes_to_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    stack.set_many({"a": 1, "b": 2})

    assert l1_cache.get("a") == 1
    assert l1_cache.get("b") == 2
    assert l2_cache.get("a") == 1
    assert l2_cache.get("b") == 2


async def test_set_many_returns_true(stack: CacheStack) -> None:
    assert stack.set_many({"a": 1}) is True


# --- has ---


async def test_has_returns_true_when_key_in_l1(
    stack: CacheStack, l1_cache: Cache
) -> None:
    l1_cache.set("key", "value")

    assert stack.has("key") is True


async def test_has_returns_true_when_key_only_in_l2(
    stack: CacheStack, l2_cache: Cache
) -> None:
    l2_cache.set("key", "value")

    assert stack.has("key") is True


async def test_has_returns_false_when_key_in_neither(stack: CacheStack) -> None:
    assert stack.has("missing") is False


# --- remember ---


async def test_remember_returns_l1_value_without_invoking_callback(
    stack: CacheStack, l1_cache: Cache
) -> None:
    l1_cache.set("key", "cached")
    calls = 0

    def callback() -> str:
        nonlocal calls
        calls += 1
        return "computed"

    result = stack.remember("key", callback)

    assert result == "cached"
    assert calls == 0


async def test_remember_executes_callback_and_populates_both_on_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    result = stack.remember("key", lambda: "computed")

    assert result == "computed"
    assert l1_cache.get("key") == "computed"
    assert l2_cache.get("key") == "computed"


async def test_remember_populates_l1_from_l2_on_l1_miss(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l2_cache.set("key", "l2_value")
    calls = 0

    def callback() -> str:
        nonlocal calls
        calls += 1
        return "computed"

    result = stack.remember("key", callback)

    assert result == "l2_value"
    assert l1_cache.get("key") == "l2_value"
    assert calls == 0


# --- delete ---


async def test_delete_removes_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("key", "value")
    l2_cache.set("key", "value")

    stack.delete("key")

    assert l1_cache.get("key") is None
    assert l2_cache.get("key") is None


async def test_delete_returns_true(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("key", "value")
    l2_cache.set("key", "value")

    assert stack.delete("key") is True


# --- delete_many ---


async def test_delete_many_removes_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set_many({"a": 1, "b": 2})
    l2_cache.set_many({"a": 1, "b": 2})

    stack.delete_many(["a", "b"])

    assert l1_cache.get("a") is None
    assert l1_cache.get("b") is None
    assert l2_cache.get("a") is None
    assert l2_cache.get("b") is None


async def test_delete_many_returns_true(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set_many({"a": 1})
    l2_cache.set_many({"a": 1})

    assert stack.delete_many(["a"]) is True


# --- clear ---


async def test_clear_removes_all_from_both_caches(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set_many({"a": 1, "b": 2})
    l2_cache.set_many({"c": 3, "d": 4})

    stack.clear()

    assert l1_cache.get("a") is None
    assert l1_cache.get("b") is None
    assert l2_cache.get("c") is None
    assert l2_cache.get("d") is None


async def test_clear_returns_true(stack: CacheStack) -> None:
    assert stack.clear() is True


# --- pop ---


async def test_pop_returns_l1_value_and_removes_from_both(
    stack: CacheStack, l1_cache: Cache, l2_cache: Cache
) -> None:
    l1_cache.set("key", "l1_value")
    l2_cache.set("key", "l2_value")

    result = stack.pop("key")

    assert result == "l1_value"
    assert l1_cache.get("key") is None
    assert l2_cache.get("key") is None


async def test_pop_returns_l2_value_and_removes_it_on_l1_miss(
    stack: CacheStack, l2_cache: Cache
) -> None:
    l2_cache.set("key", "l2_value")

    result = stack.pop("key")

    assert result == "l2_value"
    assert l2_cache.get("key") is None


async def test_pop_returns_none_when_both_miss(stack: CacheStack) -> None:
    assert stack.pop("missing") is None


# --- lock ---


async def test_lock_delegates_to_l2_cache(stack: CacheStack, l2_cache: Cache) -> None:
    stack_lock = stack.lock("my-lock")
    l2_lock = l2_cache.lock("my-lock")

    assert type(stack_lock) is type(l2_lock)
