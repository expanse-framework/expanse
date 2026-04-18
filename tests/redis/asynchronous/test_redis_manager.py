from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from expanse.configuration.config import Config
from expanse.redis.asynchronous.redis_manager import RedisManager
from expanse.redis.exceptions import UnconfiguredConnectionError


@pytest.fixture()
def config() -> Config:
    return Config(
        {
            "redis": {
                "connection": "default",
                "connections": {
                    "default": {
                        "url": "redis://localhost:6379/0",
                    },
                    "cache": {
                        "url": "redis://localhost:6379/1",
                        "max_retries": 5,
                        "backoff": {
                            "strategy": "constant",
                            "backoff": 2,
                        },
                    },
                },
            }
        }
    )


def test_get_default_connection_name(config: Config) -> None:
    manager = RedisManager(config)

    assert manager.get_default_connection_name() == "default"


def test_get_default_connection_name_uses_config(config: Config) -> None:
    config["redis.connection"] = "cache"

    manager = RedisManager(config)

    assert manager.get_default_connection_name() == "cache"


async def test_connection_raises_for_unconfigured_name(config: Config) -> None:
    manager = RedisManager(config)

    with pytest.raises(UnconfiguredConnectionError, match="'nonexistent'"):
        await manager.connection("nonexistent")


async def test_connection_caches_connections(config: Config) -> None:
    manager = RedisManager(config)
    mock_connection = MagicMock()

    with patch.object(
        manager, "_create_connection", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_connection

        conn1 = await manager.connection("default")
        conn2 = await manager.connection("default")

    assert conn1 is conn2
    mock_create.assert_called_once()


async def test_connection_uses_default_when_name_is_none(config: Config) -> None:
    manager = RedisManager(config)
    mock_connection = MagicMock()

    with patch.object(
        manager, "_create_connection", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_connection

        conn = await manager.connection()

    assert conn is mock_connection
    mock_create.assert_called_once_with({"url": "redis://localhost:6379/0"})


async def test_close_closes_all_connections(config: Config) -> None:
    manager = RedisManager(config)
    mock_conn1 = AsyncMock()
    mock_conn2 = AsyncMock()

    with patch.object(
        manager, "_create_connection", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = [mock_conn1, mock_conn2]

        await manager.connection("default")
        await manager.connection("cache")

    await manager.close()

    mock_conn1.aclose.assert_called_once()
    mock_conn2.aclose.assert_called_once()


async def test_close_with_no_connections(config: Config) -> None:
    manager = RedisManager(config)

    await manager.close()
