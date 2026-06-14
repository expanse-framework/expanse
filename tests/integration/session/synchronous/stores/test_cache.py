import json

import pytest

from expanse.cache.synchronous.cache import Cache
from expanse.cache.synchronous.stores.memory import MemoryStore
from expanse.session.synchronous.stores.cache import CacheStore


@pytest.fixture()
def cache() -> Cache:
    return Cache("cache", MemoryStore())


def test_store_can_read_from_the_cache(cache: Cache) -> None:
    session_id = "s" * 40

    store = CacheStore(cache, 120)

    assert store.read(session_id) == ""

    cache.set(session_id, json.dumps({"foo": "bar"}), 120 * 60)

    assert store.read(session_id) == json.dumps({"foo": "bar"})


def test_store_can_write_data_to_the_cache(cache: Cache) -> None:
    session_id = "s" * 40

    store = CacheStore(cache, 120)

    assert cache.get(session_id) is None

    store.write(session_id, json.dumps({"bar": "baz"}))

    assert cache.get(session_id) == json.dumps({"bar": "baz"})


def test_store_can_delete_sessions(cache: Cache) -> None:
    session_id = "s" * 40

    store = CacheStore(cache, 120)

    cache.set(session_id, json.dumps({"foo": "bar"}), 120 * 60)

    store.delete(session_id)

    assert cache.get(session_id) is None


def test_expired_sessions_can_be_cleared(cache: Cache) -> None:
    session_id = "s" * 40

    store = CacheStore(cache, 0)

    cache.set(session_id, json.dumps({"foo": "bar"}), 0 * 60)

    assert store.clear() == 0

    assert store.read(session_id) == ""
