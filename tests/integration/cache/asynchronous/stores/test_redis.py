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
    from expanse.redis.asynchronous.connections.connection import Connection


pytestmark = pytest.mark.redis


@pytest.fixture(autouse=True)
async def setup_redis(app: Application) -> AsyncGenerator[None]:
    from expanse.redis.redis_service_provider import RedisServiceProvider

    app.config["redis"] = {
        "connection": "default",
        "connections": {
            "default": {
                "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1"
            }
        },
    }

    await RedisServiceProvider(app.container).register()

    yield

    manager = await app.container.get(RedisManager)
    connection = await manager.connection("default")
    await connection.flushdb()


@pytest.fixture()
async def connection(app: Application) -> Connection:
    manager = await app.container.get(RedisManager)

    return await manager.connection("default")


@pytest.fixture()
async def store(connection: Connection) -> RedisStore:
    return RedisStore(connection)


async def test_set_stores_value(store: RedisStore) -> None:
    result = await store.set("key", "value")

    assert result is True
    assert await store.get("key") == "value"


async def test_set_overwrites_existing_value(store: RedisStore) -> None:
    await store.set("key", "original")
    await store.set("key", "updated")

    assert await store.get("key") == "updated"


async def test_set_stores_complex_value(store: RedisStore) -> None:
    value = {"nested": [1, 2, 3], "flag": True}

    await store.set("key", value)

    assert await store.get("key") == value


async def test_set_with_ttl_stores_value(store: RedisStore) -> None:
    result = await store.set("key", "value", ttl=60)

    assert result is True
    assert await store.get("key") == "value"


async def test_set_with_ttl_sets_expiration(
    store: RedisStore, connection: Connection
) -> None:
    await store.set("key", "value", ttl=60)

    ttl = await connection.ttl("key")

    assert 0 < ttl <= 60


async def test_get_returns_none_for_missing_key(store: RedisStore) -> None:
    assert await store.get("missing") is None


async def test_get_returns_none_for_expired_key(
    store: RedisStore, connection: Connection
) -> None:
    await store.set("key", "value")
    await connection.pexpire("key", 1)
    await asyncio.sleep(0.01)

    assert await store.get("key") is None


async def test_set_many_stores_multiple_values(store: RedisStore) -> None:
    result = await store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert await store.get("a") == 1
    assert await store.get("b") == 2
    assert await store.get("c") == 3


async def test_set_many_with_ttl_stores_values(
    store: RedisStore, connection: Connection
) -> None:
    result = await store.set_many({"x": 10, "y": 20}, ttl=60)

    assert result is True

    ttl_x = await connection.ttl("x")
    ttl_y = await connection.ttl("y")

    assert 0 < ttl_x <= 60
    assert 0 < ttl_y <= 60


async def test_get_many_returns_values_for_existing_keys(store: RedisStore) -> None:
    await store.set_many({"x": 10, "y": 20})

    result = await store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


async def test_get_many_returns_none_for_missing_keys(store: RedisStore) -> None:
    await store.set("x", 10)

    result = await store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


async def test_get_many_returns_empty_dict_for_empty_keys(store: RedisStore) -> None:
    result = await store.get_many([])

    assert result == {}


async def test_has_returns_true_for_existing_key(store: RedisStore) -> None:
    await store.set("key", "value")

    assert await store.has("key") is True


async def test_has_returns_false_for_missing_key(store: RedisStore) -> None:
    assert await store.has("missing") is False


async def test_has_returns_false_for_expired_key(
    store: RedisStore, connection: Connection
) -> None:
    await store.set("key", "value")
    await connection.pexpire("key", 1)
    await asyncio.sleep(0.01)

    assert await store.has("key") is False


async def test_delete_removes_key(store: RedisStore) -> None:
    await store.set("key", "value")

    result = await store.delete("key")

    assert result is True
    assert await store.get("key") is None


async def test_delete_returns_false_for_missing_key(store: RedisStore) -> None:
    result = await store.delete("missing")

    assert result is False


async def test_clear_removes_all_entries(store: RedisStore) -> None:
    await store.set_many({"a": 1, "b": 2})

    result = await store.clear()

    assert result is True
    assert await store.get("a") is None
    assert await store.get("b") is None
