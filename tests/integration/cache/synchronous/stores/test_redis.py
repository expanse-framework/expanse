from __future__ import annotations

import os
import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.stores.redis.store import RedisStore
from expanse.redis.synchronous.redis_manager import RedisManager


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.core.application import Application


pytestmark = pytest.mark.redis


@pytest.fixture(autouse=True)
async def setup_redis(app: Application) -> AsyncGenerator[None]:
    from expanse.redis.redis_service_provider import RedisServiceProvider

    app.config["redis"] = {
        "connection": "default",
        "connections": {
            "default": {
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1"
            },
            "lock": {
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/2"
            },
        },
    }

    await RedisServiceProvider(app.container).register()

    yield

    manager = await app.container.get(RedisManager)
    connection = manager.connection("default")
    connection.flushdb()


@pytest.fixture()
async def redis(app: Application) -> RedisManager:
    manager = await app.container.get(RedisManager)

    return manager


@pytest.fixture()
def store(redis: RedisManager) -> RedisStore:
    return RedisStore(redis)


def test_set_stores_value(store: RedisStore) -> None:
    result = store.set("key", "value")

    assert result is True
    assert store.get("key") == "value"


def test_set_overwrites_existing_value(store: RedisStore) -> None:
    store.set("key", "original")
    store.set("key", "updated")

    assert store.get("key") == "updated"


def test_set_stores_complex_value(store: RedisStore) -> None:
    value = {"nested": [1, 2, 3], "flag": True}

    store.set("key", value)

    assert store.get("key") == value


def test_set_with_ttl_stores_value(store: RedisStore) -> None:
    result = store.set("key", "value", ttl=60)

    assert result is True
    assert store.get("key") == "value"


def test_set_with_ttl_sets_expiration(store: RedisStore, redis: RedisManager) -> None:
    store.set("key", "value", ttl=60)

    connection = redis.connection("default")
    ttl = connection.ttl("key")

    assert 0 < ttl <= 60


def test_get_returns_none_for_missing_key(store: RedisStore) -> None:
    assert store.get("missing") is None


def test_get_returns_none_for_expired_key(
    store: RedisStore, redis: RedisManager
) -> None:
    store.set("key", "value")
    connection = redis.connection("default")
    connection.pexpire("key", 1)
    time.sleep(0.01)

    assert store.get("key") is None


def test_set_many_stores_multiple_values(store: RedisStore) -> None:
    result = store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert store.get("a") == 1
    assert store.get("b") == 2
    assert store.get("c") == 3


def test_set_many_with_ttl_stores_values(
    store: RedisStore, redis: RedisManager
) -> None:
    result = store.set_many({"x": 10, "y": 20}, ttl=60)

    assert result is True

    connection = redis.connection("default")
    ttl_x = connection.ttl("x")
    ttl_y = connection.ttl("y")

    assert 0 < ttl_x <= 60
    assert 0 < ttl_y <= 60


def test_get_many_returns_values_for_existing_keys(store: RedisStore) -> None:
    store.set_many({"x": 10, "y": 20})

    result = store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


def test_get_many_returns_none_for_missing_keys(store: RedisStore) -> None:
    store.set("x", 10)

    result = store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


def test_get_many_returns_empty_dict_for_empty_keys(store: RedisStore) -> None:
    result = store.get_many([])

    assert result == {}


def test_has_returns_true_for_existing_key(store: RedisStore) -> None:
    store.set("key", "value")

    assert store.has("key") is True


def test_has_returns_false_for_missing_key(store: RedisStore) -> None:
    assert store.has("missing") is False


def test_has_returns_false_for_expired_key(
    store: RedisStore, redis: RedisManager
) -> None:
    store.set("key", "value")
    connection = redis.connection("default")
    connection.pexpire("key", 1)
    time.sleep(0.01)

    assert store.has("key") is False


def test_delete_removes_key(store: RedisStore) -> None:
    store.set("key", "value")

    result = store.delete("key")

    assert result is True
    assert store.get("key") is None


def test_delete_returns_false_for_missing_key(store: RedisStore) -> None:
    result = store.delete("missing")

    assert result is False


def test_clear_removes_all_entries(store: RedisStore) -> None:
    store.set_many({"a": 1, "b": 2})

    result = store.clear()

    assert result is True
    assert store.get("a") is None
    assert store.get("b") is None


def test_lock_acquire_and_release(store: RedisStore) -> None:
    lock = store.lock("test-lock", ttl=10)

    acquired = lock.acquire(blocking=False)
    assert acquired is True

    released = lock.release()
    assert released is True


def test_lock_uses_lock_connection(redis: RedisManager) -> None:
    store = RedisStore(redis, connection_name="default", lock_connection_name="lock")
    lock = store.lock("test-lock")

    with lock:
        connection = redis.connection("default")
        assert connection.get("lock:test-lock") is None

        lock_connection = redis.connection("lock")
        assert lock_connection.get("lock:test-lock") == lock.owner
