from __future__ import annotations

import pytest

from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore


@pytest.fixture()
def store() -> MemoryStore:
    return MemoryStore(SyncMemoryStore())


async def test_set_stores_value(store: MemoryStore) -> None:
    result = await store.set("key", "value")

    assert result is True
    assert await store.get("key") == "value"


def test_set_overwrites_existing_key(store: MemoryStore) -> None:
    store._sync_store.set("key", "original")
    store._sync_store.set("key", "updated")

    assert store._sync_store.get("key") == "updated"


async def test_set_accepts_ttl_parameter(store: MemoryStore) -> None:
    result = await store.set("key", "value", ttl=60)

    assert result is True
    assert await store.get("key") == "value"


async def test_set_many_stores_multiple_values(store: MemoryStore) -> None:
    result = await store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert await store.get("a") == 1
    assert await store.get("b") == 2
    assert await store.get("c") == 3


async def test_get_returns_stored_value(store: MemoryStore) -> None:
    await store.set("key", "value")

    assert await store.get("key") == "value"


async def test_get_returns_none_for_missing_key(store: MemoryStore) -> None:
    assert await store.get("missing") is None


async def test_get_many_returns_values_for_existing_keys(store: MemoryStore) -> None:
    await store.set_many({"x": 10, "y": 20})

    result = await store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


async def test_get_many_returns_none_for_missing_keys(store: MemoryStore) -> None:
    await store.set("x", 10)

    result = await store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


async def test_has_returns_true_for_existing_key(store: MemoryStore) -> None:
    await store.set("key", "value")

    assert await store.has("key") is True


async def test_has_returns_false_for_missing_key(store: MemoryStore) -> None:
    assert await store.has("missing") is False


async def test_delete_removes_key(store: MemoryStore) -> None:
    await store.set("key", "value")

    result = await store.delete("key")

    assert result is True
    assert await store.get("key") is None


async def test_delete_returns_false_for_missing_key(store: MemoryStore) -> None:
    result = await store.delete("missing")

    assert result is False


async def test_clear_removes_all_keys(store: MemoryStore) -> None:
    await store.set_many({"a": 1, "b": 2})

    result = await store.clear()

    assert result is True
    assert await store.get("a") is None
    assert await store.get("b") is None
