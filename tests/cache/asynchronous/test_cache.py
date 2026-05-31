from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.locker import Locker
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore


@pytest.fixture()
def sync_store() -> SyncMemoryStore:
    return SyncMemoryStore()


@pytest.fixture()
def store(sync_store: SyncMemoryStore) -> MemoryStore:
    return MemoryStore(sync_store)


@pytest.fixture()
def cache(store: MemoryStore) -> Cache:
    return Cache("test", store)


@pytest.fixture()
def cache_with_locker(store: MemoryStore) -> Cache:
    return Cache("test", store, locker=Locker(store))


async def test_set_stores_value(cache: Cache) -> None:
    result = await cache.set("key", "value")

    assert result is True
    assert await cache.get("key") == "value"


async def test_set_with_ttl_stores_value(cache: Cache) -> None:
    result = await cache.set("key", "value", ttl=60)

    assert result is True
    assert await cache.get("key") == "value"


async def test_set_with_until_stores_value(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    result = await cache.set("key", "value", until=until)

    assert result is True
    assert await cache.get("key") == "value"


async def test_set_raises_when_both_ttl_and_until_given(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    with pytest.raises(
        ValueError, match=r"Cannot specify both 'ttl' and 'until' parameters."
    ):
        await cache.set("key", "value", ttl=60, until=until)


async def test_set_with_zero_ttl_deletes_existing_key(cache: Cache) -> None:
    await cache.set("key", "value")

    result = await cache.set("key", "new_value", ttl=0)

    assert result is True
    assert await cache.get("key") is None


async def test_set_with_negative_ttl_deletes_existing_key(cache: Cache) -> None:
    await cache.set("key", "value")

    result = await cache.set("key", "new_value", ttl=-10)

    assert result is True
    assert await cache.get("key") is None


async def test_set_with_expired_until_deletes_existing_key(cache: Cache) -> None:
    await cache.set("key", "value")
    past = datetime.now(UTC) - timedelta(seconds=1)

    result = await cache.set("key", "new_value", until=past)

    assert result is True
    assert await cache.get("key") is None


async def test_set_many_stores_multiple_values(cache: Cache) -> None:
    result = await cache.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert await cache.get("a") == 1
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3


async def test_set_many_with_ttl_stores_values(cache: Cache) -> None:
    result = await cache.set_many({"a": 1, "b": 2}, ttl=60)

    assert result is True
    assert await cache.get("a") == 1
    assert await cache.get("b") == 2


async def test_set_many_with_until_stores_values(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    result = await cache.set_many({"a": 1, "b": 2}, until=until)

    assert result is True
    assert await cache.get("a") == 1
    assert await cache.get("b") == 2


async def test_set_many_raises_when_both_ttl_and_until_given(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    with pytest.raises(
        ValueError, match=r"Cannot specify both 'ttl' and 'until' parameters."
    ):
        await cache.set_many({"a": 1}, ttl=60, until=until)


async def test_set_many_with_zero_ttl_deletes_existing_keys(cache: Cache) -> None:
    await cache.set_many({"a": 1, "b": 2})

    result = await cache.set_many({"a": 99, "b": 99}, ttl=0)

    assert result is True
    assert await cache.get("a") is None
    assert await cache.get("b") is None


async def test_get_returns_stored_value(cache: Cache) -> None:
    await cache.set("key", "value")

    assert await cache.get("key") == "value"


async def test_get_returns_none_for_missing_key(cache: Cache) -> None:
    assert await cache.get("missing") is None


async def test_get_returns_default_for_missing_key(cache: Cache) -> None:
    assert await cache.get("missing", "fallback") == "fallback"


async def test_get_returns_stored_value_ignoring_default(cache: Cache) -> None:
    await cache.set("key", "value")

    assert await cache.get("key", "fallback") == "value"


async def test_get_many_with_list_returns_all_values(cache: Cache) -> None:
    await cache.set_many({"x": 10, "y": 20})

    result = await cache.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


async def test_get_many_with_list_returns_none_for_missing(cache: Cache) -> None:
    await cache.set("x", 10)

    result = await cache.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


async def test_get_many_with_dict_uses_dict_keys(cache: Cache) -> None:
    await cache.set_many({"x": 10, "y": 20})

    result = await cache.get_many({"x": None, "y": None})

    assert result == {"x": 10, "y": 20}


async def test_has_returns_true_for_existing_key(cache: Cache) -> None:
    await cache.set("key", "value")

    assert await cache.has("key") is True


async def test_has_returns_false_for_missing_key(cache: Cache) -> None:
    assert await cache.has("missing") is False


async def test_has_returns_false_after_deletion(cache: Cache) -> None:
    await cache.set("key", "value")
    await cache.delete("key")

    assert await cache.has("key") is False


async def test_pop_returns_value_and_removes_key(cache: Cache) -> None:
    await cache.set("key", "value")

    result = await cache.pop("key")

    assert result == "value"
    assert await cache.has("key") is False


async def test_pop_returns_none_for_missing_key(cache: Cache) -> None:
    result = await cache.pop("missing")

    assert result is None


async def test_delete_removes_key(cache: Cache) -> None:
    await cache.set("key", "value")

    result = await cache.delete("key")

    assert result is True
    assert await cache.get("key") is None


async def test_delete_returns_false_for_missing_key(cache: Cache) -> None:
    result = await cache.delete("missing")

    assert result is False


async def test_delete_many_removes_all_keys(cache: Cache) -> None:
    await cache.set_many({"a": 1, "b": 2, "c": 3})

    result = await cache.delete_many(["a", "b", "c"])

    assert result is True
    assert await cache.get("a") is None
    assert await cache.get("b") is None
    assert await cache.get("c") is None


async def test_delete_many_returns_false_when_key_missing(cache: Cache) -> None:
    await cache.set("a", 1)

    result = await cache.delete_many(["a", "missing"])

    assert result is False
    assert await cache.get("a") is None


async def test_clear_removes_all_keys(cache: Cache) -> None:
    await cache.set_many({"a": 1, "b": 2})

    result = await cache.clear()

    assert result is True
    assert await cache.get("a") is None
    assert await cache.get("b") is None


async def test_remember_stores_value_from_sync_callback(cache: Cache) -> None:
    result = await cache.remember("key", lambda: "computed")

    assert result == "computed"
    assert await cache.get("key") == "computed"


async def test_remember_stores_value_from_async_callback(cache: Cache) -> None:
    async def callback() -> str:
        return "computed"

    result = await cache.remember("key", callback)

    assert result == "computed"
    assert await cache.get("key") == "computed"


async def test_remember_returns_cached_value_without_calling_callback(
    cache: Cache,
) -> None:
    await cache.set("key", "cached")
    call_count = 0

    def callback() -> str:
        nonlocal call_count
        call_count += 1
        return "new"

    result = await cache.remember("key", callback)

    assert result == "cached"
    assert call_count == 0


async def test_remember_propagates_ttl(cache: Cache) -> None:
    result = await cache.remember("key", lambda: "value", ttl=60)

    assert result == "value"
    assert await cache.get("key") == "value"


async def test_remember_with_locker_stores_value(
    cache_with_locker: Cache,
) -> None:
    result = await cache_with_locker.remember("key", lambda: "computed")

    assert result == "computed"
    assert await cache_with_locker.get("key") == "computed"


async def test_remember_with_locker_prevents_stampede(
    cache_with_locker: Cache,
) -> None:
    import asyncio

    call_count = 0

    async def slow_callback() -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return "computed"

    results = await asyncio.gather(
        *[cache_with_locker.remember("key", slow_callback, ttl=60) for _ in range(5)]
    )

    assert all(r == "computed" for r in results)
    assert call_count == 1


async def test_remember_without_locker_does_not_prevent_stampede(
    cache: Cache,
) -> None:
    import asyncio

    call_count = 0

    async def slow_callback() -> str:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return "computed"

    results = await asyncio.gather(
        *[cache.remember("key", slow_callback, ttl=60) for _ in range(5)]
    )

    assert all(r == "computed" for r in results)
    assert call_count > 1
