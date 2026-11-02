import os

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.database.synchronous.connection import Connection
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.synchronous.transport_manager import TransportManager
from expanse.messenger.synchronous.transports.database import DatabaseTransport
from expanse.messenger.synchronous.transports.memory import MemoryTransport
from expanse.messenger.synchronous.transports.outbox import OutboxTransport
from expanse.messenger.synchronous.transports.redis import RedisTransport
from expanse.messenger.synchronous.transports.sync import SyncTransport


@dataclass
class FooMessage:
    value: str


@pytest.fixture()
def connection() -> Connection:
    # Database transports do not touch the connection until they are used
    return MagicMock(spec=Connection)


@pytest.fixture()
def make_manager(
    serializer: Serializer, connection: Connection
) -> Callable[[dict[str, Any] | None], TransportManager]:
    def _make_manager(
        messenger_config: dict[str, Any] | None = None,
    ) -> TransportManager:
        container = Container()
        config = Config(
            {
                "messenger": messenger_config or {},
                "redis": {
                    "connections": {
                        "default": {
                            "url": f"redis://localhost:{os.getenv('REDIS_TEST_PORT', '6379')}/15"
                        }
                    }
                },
            }
        )
        container.instance(Config, config)
        container.instance(Connection, connection)

        return TransportManager(container, config, Registry(), serializer)

    return _make_manager


def test_transport_returns_default_transport(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {"transport": "memory", "transports": {"memory": {"driver": "memory"}}}
    )

    assert isinstance(manager.transport(), MemoryTransport)


def test_transport_caches_transport_instance(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {"transport": "memory", "transports": {"memory": {"driver": "memory"}}}
    )

    assert manager.transport("memory") is manager.transport("memory")


@pytest.mark.parametrize(
    ("driver", "transport_class"),
    [
        ("sync", SyncTransport),
        ("memory", MemoryTransport),
        ("database", DatabaseTransport),
        ("redis", RedisTransport),
    ],
)
def test_transport_creates_transports_for_their_driver(
    make_manager: Callable[..., TransportManager],
    driver: str,
    transport_class: type[Any],
) -> None:
    manager = make_manager({"transports": {"transport": {"driver": driver}}})

    assert isinstance(manager.transport("transport"), transport_class)


def test_database_transport_uses_the_scoped_connection(
    make_manager: Callable[..., TransportManager], connection: Connection
) -> None:
    manager = make_manager({"transports": {"database": {"driver": "database"}}})

    transport = manager.transport("database")

    assert isinstance(transport, DatabaseTransport)
    assert transport.connection is connection


def test_get_default_transport_name_raises_when_not_configured(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager({"transports": {"memory": {"driver": "memory"}}})

    with pytest.raises(NoDefaultTransportError):
        manager.transport()


def test_transport_raises_for_unconfigured_transport(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager({"transports": {}})

    with pytest.raises(UnconfiguredTransportError):
        manager.transport("unknown")


def test_transport_raises_when_driver_missing(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager({"transports": {"broken": {}}})

    with pytest.raises(UnconfiguredTransportError):
        manager.transport("broken")


def test_transport_raises_for_unsupported_driver(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager({"transports": {"broken": {"driver": "unknown"}}})

    with pytest.raises(UnsupportedTransportDriverError):
        manager.transport("broken")


def test_transport_wraps_transport_configured_with_an_outbox(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "outbox"},
                "outbox": {"driver": "database"},
            }
        }
    )

    transport = manager.transport("memory")

    assert isinstance(transport, OutboxTransport)
    assert isinstance(transport.target_transport, MemoryTransport)
    assert transport.outbox_transport is manager.transport("outbox")


def test_transport_is_not_wrapped_when_outbox_is_empty(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {"transports": {"memory": {"driver": "memory", "outbox": None}}}
    )

    assert isinstance(manager.transport("memory"), MemoryTransport)


def test_transport_raises_when_outbox_is_not_a_database_transport(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "other"},
                "other": {"driver": "memory"},
            }
        }
    )

    with pytest.raises(InvalidOutboxTransportError):
        manager.transport("memory")


def test_transport_raises_on_circular_outbox_configuration(
    make_manager: Callable[..., TransportManager],
) -> None:
    manager = make_manager(
        {"transports": {"database": {"driver": "database", "outbox": "database"}}}
    )

    with pytest.raises(InvalidOutboxTransportError):
        manager.transport("database")
