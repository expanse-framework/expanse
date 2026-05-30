from __future__ import annotations

import asyncio
import os

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.stores.redis.store import RedisStore
from expanse.redis.asynchronous.redis_manager import RedisManager


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
    await connection.flushdb()


@pytest.fixture()
async def redis(app: Application) -> RedisManager:
    manager = await app.container.get(RedisManager)

    return manager


@pytest.fixture()
async def store(redis: RedisManager) -> RedisStore:
    return RedisStore(redis)


async def test_set_stores_value(store: RedisStore) -> None:
    result = await store.set("key", "value")

    assert result is True
    assert (await store.get("key")).value == "value"


async def test_set_overwrites_existing_value(store: RedisStore) -> None:
    await store.set("key", "original")
    await store.set("key", "updated")

    assert (await store.get("key")).value == "updated"


async def test_set_stores_complex_value(store: RedisStore) -> None:
    value = {"nested": [1, 2, 3], "flag": True}

    await store.set("key", value)

    assert (await store.get("key")).value == value


async def test_set_with_ttl_stores_value(store: RedisStore) -> None:
    result = await store.set("key", "value", ttl=60)

    assert result is True
    assert (await store.get("key")).value == "value"


async def test_set_with_ttl_sets_expiration(
    store: RedisStore, redis: RedisManager
) -> None:
    await store.set("key", "value", ttl=60)
    connection = redis.connection("default")

    ttl = await connection.ttl("key")

    assert 0 < ttl <= 60


async def test_get_returns_miss_for_missing_key(store: RedisStore) -> None:
    assert (await store.get("missing")).is_hit is False


async def test_get_returns_miss_for_expired_key(
    store: RedisStore, redis: RedisManager
) -> None:
    await store.set("key", "value")
    connection = redis.connection("default")
    await connection.pexpire("key", 1)
    await asyncio.sleep(0.01)

    assert (await store.get("key")).is_hit is False


async def test_set_many_stores_multiple_values(store: RedisStore) -> None:
    result = await store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert (await store.get("a")).value == 1
    assert (await store.get("b")).value == 2
    assert (await store.get("c")).value == 3


async def test_set_many_with_ttl_stores_values(
    store: RedisStore, redis: RedisManager
) -> None:
    result = await store.set_many({"x": 10, "y": 20}, ttl=60)

    assert result is True

    connection = redis.connection("default")
    ttl_x = await connection.ttl("x")
    ttl_y = await connection.ttl("y")

    assert 0 < ttl_x <= 60
    assert 0 < ttl_y <= 60


async def test_get_many_returns_hits_for_existing_keys(store: RedisStore) -> None:
    await store.set_many({"x": 10, "y": 20})

    result = await store.get_many(["x", "y"])

    assert result["x"].is_hit is True
    assert result["x"].value == 10
    assert result["y"].is_hit is True
    assert result["y"].value == 20


async def test_get_many_returns_miss_for_missing_keys(store: RedisStore) -> None:
    await store.set("x", 10)

    result = await store.get_many(["x", "missing"])

    assert result["x"].is_hit is True
    assert result["x"].value == 10
    assert result["missing"].is_hit is False


async def test_get_many_returns_empty_dict_for_empty_keys(store: RedisStore) -> None:
    result = await store.get_many([])

    assert result == {}


async def test_has_returns_true_for_existing_key(store: RedisStore) -> None:
    await store.set("key", "value")

    assert await store.has("key") is True


async def test_has_returns_false_for_missing_key(store: RedisStore) -> None:
    assert await store.has("missing") is False


async def test_has_returns_false_for_expired_key(
    store: RedisStore, redis: RedisManager
) -> None:
    await store.set("key", "value")
    connection = redis.connection("default")
    await connection.pexpire("key", 1)
    await asyncio.sleep(0.01)

    assert await store.has("key") is False


async def test_delete_removes_key(store: RedisStore) -> None:
    await store.set("key", "value")

    result = await store.delete("key")

    assert result is True
    assert (await store.get("key")).is_hit is False


async def test_delete_returns_false_for_missing_key(store: RedisStore) -> None:
    result = await store.delete("missing")

    assert result is False


async def test_clear_removes_all_entries(store: RedisStore) -> None:
    await store.set_many({"a": 1, "b": 2})

    result = await store.clear()

    assert result is True
    assert (await store.get("a")).is_hit is False
    assert (await store.get("b")).is_hit is False


async def test_lock_acquire_and_release(store: RedisStore) -> None:
    lock = store.lock("test-lock", ttl=10)

    acquired = await lock.acquire(blocking=False)
    assert acquired is True

    released = await lock.release()
    assert released is True


async def test_lock_uses_lock_connection(redis: RedisManager) -> None:
    store = RedisStore(redis, connection_name="default", lock_connection_name="lock")
    lock = store.lock("test-lock")

    async with lock:
        connection = redis.connection("default")
        assert await connection.get("lock:test-lock") is None

        lock_connection = redis.connection("lock")
        assert await lock_connection.get("lock:test-lock") == lock.owner
