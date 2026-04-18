from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from expanse.configuration.config import Config
from expanse.redis.exceptions import UnconfiguredConnectionError
from expanse.redis.synchronous.redis_manager import RedisManager


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


def test_connection_raises_for_unconfigured_name(config: Config) -> None:
    manager = RedisManager(config)

    with pytest.raises(UnconfiguredConnectionError, match="'nonexistent'"):
        manager.connection("nonexistent")


def test_connection_caches_connections(config: Config) -> None:
    manager = RedisManager(config)
    mock_connection = MagicMock()

    with patch.object(manager, "_create_connection") as mock_create:
        mock_create.return_value = mock_connection

        conn1 = manager.connection("default")
        conn2 = manager.connection("default")

    assert conn1 is conn2
    mock_create.assert_called_once()


def test_connection_uses_default_when_name_is_none(config: Config) -> None:
    manager = RedisManager(config)
    mock_connection = MagicMock()

    with patch.object(manager, "_create_connection") as mock_create:
        mock_create.return_value = mock_connection

        conn = manager.connection()

    assert conn is mock_connection
    mock_create.assert_called_once_with({"url": "redis://localhost:6379/0"})


def test_close_closes_all_connections(config: Config) -> None:
    manager = RedisManager(config)
    mock_conn1 = MagicMock()
    mock_conn2 = MagicMock()

    with patch.object(manager, "_create_connection") as mock_create:
        mock_create.side_effect = [mock_conn1, mock_conn2]

        manager.connection("default")
        manager.connection("cache")

    manager.close()

    mock_conn1.close.assert_called_once()
    mock_conn2.close.assert_called_once()


def test_close_with_no_connections(config: Config) -> None:
    manager = RedisManager(config)

    manager.close()
