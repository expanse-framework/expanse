from __future__ import annotations

import os

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.cache_manager import CacheManager
from expanse.cache.exceptions import NoDefaultStoreError
from expanse.cache.exceptions import UnconfiguredStoreError
from expanse.cache.exceptions import UnsupportedStoreDriverError
from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.core.application import Application


def make_config(store: str = "memory", stores: dict | None = None) -> Config:
    if stores is None:
        stores = {"memory": {"driver": "memory"}}
    return Config({"cache": {"store": store, "stores": stores}})


@pytest.fixture()
def config() -> Config:
    return make_config()


@pytest.fixture()
def manager(config: Config) -> CacheManager:
    return CacheManager(config, Container())


async def test_cache_returns_default_store(manager: CacheManager) -> None:
    cache = await manager.cache()

    assert isinstance(cache, Cache)


async def test_cache_returns_named_store(manager: CacheManager) -> None:
    cache = await manager.cache("memory")

    assert isinstance(cache, Cache)


async def test_cache_returns_same_instance_on_repeated_calls(
    manager: CacheManager,
) -> None:
    cache1 = await manager.cache()
    cache2 = await manager.cache()

    assert cache1 is cache2


async def test_cache_returns_same_instance_for_default_and_named(
    manager: CacheManager,
) -> None:
    default_cache = await manager.cache()
    named_cache = await manager.cache("memory")

    assert default_cache is named_cache


async def test_get_default_store_name_returns_configured_default(
    config: Config,
) -> None:
    manager = CacheManager(config, Container())

    assert manager.get_default_store_name() == "memory"


async def test_get_default_store_name_raises_when_no_default_configured() -> None:
    config = Config({"cache": {"stores": {"memory": {"driver": "memory"}}}})
    manager = CacheManager(config, Container())

    with pytest.raises(NoDefaultStoreError):
        manager.get_default_store_name()


async def test_cache_raises_when_store_not_configured(config: Config) -> None:
    manager = CacheManager(config, Container())

    with pytest.raises(UnconfiguredStoreError, match="'unknown'"):
        await manager.cache("unknown")


async def test_cache_raises_when_store_missing_driver(config: Config) -> None:
    config = make_config(stores={"bad": {}})
    manager = CacheManager(config, Container())

    with pytest.raises(UnconfiguredStoreError, match="missing a driver"):
        await manager.cache("bad")


async def test_cache_raises_for_unsupported_driver(config: Config) -> None:
    config = make_config(stores={"unknown": {"driver": "unknown"}})
    manager = CacheManager(config, Container())

    with pytest.raises(UnsupportedStoreDriverError, match="unknown"):
        await manager.cache("unknown")


async def test_set_stores_value_in_default_store(manager: CacheManager) -> None:
    result = await manager.set("key", "value")

    assert result is True
    assert await manager.get("key") == "value"


async def test_set_many_stores_multiple_values(manager: CacheManager) -> None:
    result = await manager.set_many({"a": 1, "b": 2})

    assert result is True
    assert await manager.get("a") == 1
    assert await manager.get("b") == 2


async def test_get_returns_none_for_missing_key(manager: CacheManager) -> None:
    assert await manager.get("missing") is None


async def test_get_returns_default_for_missing_key(manager: CacheManager) -> None:
    assert await manager.get("missing", "fallback") == "fallback"


async def test_get_many_returns_all_values(manager: CacheManager) -> None:
    await manager.set_many({"x": 10, "y": 20})

    result = await manager.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


async def test_has_returns_true_for_existing_key(manager: CacheManager) -> None:
    await manager.set("key", "value")

    assert await manager.has("key") is True


async def test_has_returns_false_for_missing_key(manager: CacheManager) -> None:
    assert await manager.has("missing") is False


async def test_pop_returns_value_and_removes_key(manager: CacheManager) -> None:
    await manager.set("key", "value")

    result = await manager.pop("key")

    assert result == "value"
    assert await manager.has("key") is False


async def test_delete_removes_key(manager: CacheManager) -> None:
    await manager.set("key", "value")

    result = await manager.delete("key")

    assert result is True
    assert await manager.get("key") is None


async def test_delete_many_removes_all_keys(manager: CacheManager) -> None:
    await manager.set_many({"a": 1, "b": 2})

    result = await manager.delete_many(["a", "b"])

    assert result is True
    assert await manager.get("a") is None
    assert await manager.get("b") is None


async def test_clear_removes_all_keys(manager: CacheManager) -> None:
    await manager.set_many({"a": 1, "b": 2})

    result = await manager.clear()

    assert result is True
    assert await manager.get("a") is None
    assert await manager.get("b") is None


async def test_operations_share_state_via_default_store(manager: CacheManager) -> None:
    await manager.set("key", "value")

    cache = await manager.cache()
    assert await cache.get("key") == "value"


async def test_multiple_named_stores_are_independent() -> None:
    config = Config(
        {
            "cache": {
                "store": "first",
                "stores": {
                    "first": {"driver": "memory"},
                    "second": {"driver": "memory"},
                },
            }
        }
    )
    manager = CacheManager(config, Container())

    first = await manager.cache("first")
    second = await manager.cache("second")

    await first.set("key", "from_first")

    assert await second.get("key") is None


async def test_manager_can_create_database_store(app: Application) -> None:
    app.config["database"] = {
        "connection": "sqlite",
        "connections": {
            "sqlite": {
                "driver": "sqlite",
                "database": ":memory:",
            }
        },
    }

    app.config["cache"] = {
        "store": "database",
        "stores": {
            "database": {
                "driver": "database",
                "connection": "sqlite",
            }
        },
    }
    db = await app.container.get(AsyncDatabaseManager)
    async with db.connection("sqlite") as connection:
        await connection.execute(
            """
            CREATE TABLE cache (
                key TEXT PRIMARY KEY,
                data BLOB NOT NULL,
                expiration INTEGER
            )
            """
        )
        await connection.commit()

    manager = CacheManager(app.config, app.container)

    cache = await manager.cache()
    assert await cache.set("key", "value")
    assert await cache.get("key") == "value"


async def test_manager_can_create_file_store(tmp_path: Path) -> None:
    config = Config(
        {
            "cache": {
                "store": "file",
                "stores": {
                    "file": {
                        "driver": "file",
                        "path": str(tmp_path),
                        "permissions": 0o755,
                    }
                },
            }
        }
    )
    manager = CacheManager(config, Container())

    cache = await manager.cache()
    assert await cache.set("key", "value")
    assert await cache.get("key") == "value"


async def test_manager_can_create_redis_store() -> None:
    config = Config(
        {
            "redis": {
                "connection": "default",
                "connections": {
                    "default": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1"
                    }
                },
            },
            "cache": {
                "store": "redis",
                "stores": {
                    "redis": {
                        "driver": "redis",
                        "connection": "default",
                    }
                },
            },
        }
    )

    container = Container()
    container.instance(Config, config)
    manager = CacheManager(config, container)

    cache = await manager.cache()
    assert await cache.set("key", "value")
    assert await cache.get("key") == "value"
