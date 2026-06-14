import json

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.session.asynchronous.stores.cache import AsyncCacheStore


@pytest.fixture()
def cache() -> Cache:
    return Cache("cache", MemoryStore(SyncMemoryStore()))


async def test_store_can_read_from_the_cache(cache: Cache) -> None:
    session_id = "s" * 40

    store = AsyncCacheStore(cache, 120)

    assert await store.read(session_id) == ""

    await cache.set(session_id, json.dumps({"foo": "bar"}), 120 * 60)

    assert await store.read(session_id) == json.dumps({"foo": "bar"})


async def test_store_can_write_data_to_the_cache(cache: Cache) -> None:
    session_id = "s" * 40

    store = AsyncCacheStore(cache, 120)

    assert await cache.get(session_id) is None

    await store.write(session_id, json.dumps({"bar": "baz"}))

    assert await cache.get(session_id) == json.dumps({"bar": "baz"})


async def test_store_can_delete_sessions(cache: Cache) -> None:
    session_id = "s" * 40

    store = AsyncCacheStore(cache, 120)

    await cache.set(session_id, json.dumps({"foo": "bar"}), 120 * 60)

    await store.delete(session_id)

    assert await cache.get(session_id) is None


async def test_expired_sessions_can_be_cleared(cache: Cache) -> None:
    session_id = "s" * 40

    store = AsyncCacheStore(cache, 0)

    await cache.set(session_id, json.dumps({"foo": "bar"}), 0 * 60)

    assert await store.clear() == 0

    assert await store.read(session_id) == ""
