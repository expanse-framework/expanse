import os

import pytest

from pytest_mock import MockerFixture

from expanse.configuration.config import Config
from expanse.redis.asynchronous.redis_manager import RedisManager


pytestmark = pytest.mark.redis


@pytest.fixture()
def config() -> Config:
    return Config(
        {
            "redis": {
                "connection": "default",
                "connections": {
                    "default": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/0",
                    },
                    "no_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/1",
                        "backoff": None,
                    },
                    "constant_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/2",
                        "backoff": {
                            "strategy": "constant",
                            "backoff": 1,
                        },
                    },
                    "exponential_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/3",
                        "backoff": {
                            "strategy": "exponential",
                            "base": 1,
                            "cap": 10,
                        },
                    },
                    "full_jitter_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/4",
                        "backoff": {
                            "strategy": "full_jitter",
                            "base": 1,
                            "cap": 10,
                        },
                    },
                    "equal_jitter_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/5",
                        "backoff": {
                            "strategy": "equal_jitter",
                            "base": 1,
                            "cap": 10,
                        },
                    },
                    "decorrelated_jitter_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/6",
                        "backoff": {
                            "strategy": "decorrelated_jitter",
                            "base": 1,
                            "cap": 10,
                        },
                    },
                    "exponential_with_jitter_backoff": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/7",
                        "backoff": {
                            "strategy": "exponential_with_jitter",
                            "base": 1,
                            "cap": 10,
                        },
                    },
                    "cluster": {
                        "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', 6379)}/0",
                        "cluster": True,
                    },
                },
            }
        }
    )


async def test_default_connection(config: Config) -> None:
    manager = RedisManager(config)

    try:
        connection = await manager.connection()

        await connection.set("test_key", "test_value")
        result = await connection.get("test_key")

        assert result == "test_value"
    finally:
        await manager.close()


async def test_named_connection(config: Config) -> None:
    manager = RedisManager(config)

    try:
        connection = await manager.connection("no_backoff")

        await connection.set("test_key", "test_value")
        result = await connection.get("test_key")

        assert result == "test_value"
    finally:
        await manager.close()


async def test_connection_with_no_backoff(config: Config) -> None:
    manager = RedisManager(config)

    try:
        connection = await manager.connection("no_backoff")

        assert connection.ping()
    finally:
        await manager.close()


async def test_connection_with_constant_backoff(config: Config) -> None:
    manager = RedisManager(config)

    try:
        connection = await manager.connection("constant_backoff")

        assert connection.ping()
    finally:
        await manager.close()


@pytest.mark.parametrize(
    "connection_name",
    [
        "exponential_backoff",
        "full_jitter_backoff",
        "equal_jitter_backoff",
        "decorrelated_jitter_backoff",
        "exponential_with_jitter_backoff",
    ],
)
async def test_connection_with_generic_backoff_strategies(
    config: Config, connection_name: str
) -> None:
    manager = RedisManager(config)

    try:
        connection = await manager.connection(connection_name)

        assert connection.ping()
    finally:
        await manager.close()


async def test_close_closes_all_connections(config: Config) -> None:
    manager = RedisManager(config)

    conn1 = await manager.connection("default")
    conn2 = await manager.connection("no_backoff")

    assert conn1.ping()
    assert conn2.ping()

    await manager.close()


async def test_connection_with_cluster(config: Config, mocker: MockerFixture) -> None:
    from redis.asyncio import RedisCluster

    mock = mocker.patch.object(RedisCluster, "from_url")

    manager = RedisManager(config)

    await manager.connection("cluster")

    assert mock.called
