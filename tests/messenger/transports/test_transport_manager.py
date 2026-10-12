import os

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.database.asynchronous.connection import AsyncConnection
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.transports.database.transport import DatabaseTransport
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.outbox.transport import OutboxTransport
from expanse.messenger.transports.redis.transport import RedisTransport
from expanse.messenger.transports.sync.transport import SyncTransport
from expanse.messenger.transports.transport_manager import TransportManager


@dataclass
class FooMessage:
    value: str


@pytest.fixture()
def make_manager(
    serializer: Serializer,
) -> Callable[[dict[str, Any] | None], TransportManager]:
    def _make_manager(
        messenger_config: dict[str, Any] | None = None,
    ) -> TransportManager:
        container = Container()
        registry = Registry()
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
        container.instance(SerializerContract, serializer)
        # Database transports do not touch the connection until they are used
        container.instance(AsyncConnection, MagicMock(spec=AsyncConnection))

        return TransportManager(container, config, registry)

    return _make_manager


async def test_transport_returns_default_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transport": "memory",
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    transport = await manager.transport()

    assert isinstance(transport, MemoryTransport)


async def test_transport_returns_named_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transport": "memory",
            "transports": {
                "memory": {"driver": "memory"},
                "sync": {"driver": "sync"},
            },
        }
    )

    transport = await manager.transport("sync")

    assert isinstance(transport, SyncTransport)


async def test_transport_caches_transport_instance(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transport": "memory",
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    first = await manager.transport("memory")
    second = await manager.transport("memory")

    assert first is second


async def test_transport_creates_memory_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    transport = await manager.transport("memory")

    assert isinstance(transport, MemoryTransport)


async def test_transport_creates_sync_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "sync": {"driver": "sync"},
            },
        }
    )

    transport = await manager.transport("sync")

    assert isinstance(transport, SyncTransport)


async def test_transport_creates_redis_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "sync": {"driver": "redis", "connection": "default"},
            },
        }
    )

    transport = await manager.transport("sync")

    assert isinstance(transport, RedisTransport)


async def test_get_default_transport_name_returns_configured_name(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({"transport": "my_transport"})

    assert manager.get_default_transport_name() == "my_transport"


async def test_get_default_transport_name_raises_when_not_configured(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({})

    with pytest.raises(NoDefaultTransportError):
        manager.get_default_transport_name()


async def test_transport_raises_for_unconfigured_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    with pytest.raises(UnconfiguredTransportError, match="'unknown' is not configured"):
        await manager.transport("unknown")


async def test_transport_raises_when_driver_missing(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "broken": {"some_key": "some_value"},
            },
        }
    )

    with pytest.raises(
        UnconfiguredTransportError, match="'broken' is missing a driver"
    ):
        await manager.transport("broken")


async def test_transport_raises_for_unsupported_driver(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "custom": {"driver": "invalid"},
            },
        }
    )

    with pytest.raises(
        UnsupportedTransportDriverError, match="unsupported driver 'invalid'"
    ):
        await manager.transport("custom")


async def test_transport_without_name_raises_when_no_default(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    with pytest.raises(NoDefaultTransportError):
        await manager.transport()


async def test_different_transports_are_cached_independently(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
                "sync": {"driver": "sync"},
            },
        }
    )

    memory = await manager.transport("memory")
    sync = await manager.transport("sync")

    assert isinstance(memory, MemoryTransport)
    assert isinstance(sync, SyncTransport)
    assert memory is not sync


async def test_transport_wraps_transport_configured_with_an_outbox(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "outbox"},
                "outbox": {"driver": "database"},
            },
        }
    )

    transport = await manager.transport("memory")

    assert isinstance(transport, OutboxTransport)
    assert isinstance(transport.target_transport, MemoryTransport)


async def test_outbox_transport_stores_messages_in_the_configured_outbox(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "outbox"},
                "outbox": {"driver": "database"},
            },
        }
    )

    transport = await manager.transport("memory")
    outbox = await manager.transport("outbox")
    assert isinstance(outbox, DatabaseTransport)

    sent: list[Envelope] = []

    async def send(envelope: Envelope) -> Envelope:
        sent.append(envelope)

        return envelope

    outbox.send = send  # type: ignore[method-assign]

    await transport.send(Envelope.wrap(FooMessage(value="hello")))

    assert len(sent) == 1
    assert sent[0].stamp(OutboxStamp) == OutboxStamp(target_transport_name="memory")


@pytest.mark.parametrize("outbox", [None, ""])
async def test_transport_is_not_wrapped_when_outbox_is_empty(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
    outbox: str | None,
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": outbox},
            },
        }
    )

    transport = await manager.transport("memory")

    assert isinstance(transport, MemoryTransport)


async def test_transport_raises_when_outbox_is_not_a_database_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "other"},
                "other": {"driver": "memory"},
            },
        }
    )

    with pytest.raises(
        InvalidOutboxTransportError,
        match="must be a database transport",
    ):
        await manager.transport("memory")


@pytest.mark.parametrize(
    "transports",
    [
        {"database": {"driver": "database", "outbox": "database"}},
        {
            "memory": {"driver": "memory", "outbox": "outbox"},
            "outbox": {"driver": "database", "outbox": "memory"},
        },
    ],
    ids=["self", "mutual"],
)
async def test_transport_raises_on_circular_outbox_configuration(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
    transports: dict[str, Any],
) -> None:
    manager = make_manager({"transports": transports})

    with pytest.raises(InvalidOutboxTransportError, match="Circular outbox"):
        await manager.transport(next(iter(transports)))


def _make_database_manager() -> MagicMock:
    db = MagicMock(spec=AsyncDatabaseManager)
    db.get_default_connection.return_value = "default"
    db.connection.side_effect = lambda name: MagicMock(spec=AsyncConnection)

    return db


@pytest.mark.parametrize("connection", [None, "default"])
async def test_database_transport_uses_the_scoped_connection_for_the_default_connection(
    serializer: Serializer, connection: str | None
) -> None:
    scoped_connection = MagicMock(spec=AsyncConnection)
    db = _make_database_manager()
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, scoped_connection)
    container.instance(AsyncDatabaseManager, db)
    config = Config(
        {
            "messenger": {
                "transports": {
                    "database": {"driver": "database", "connection": connection}
                }
            }
        }
    )
    manager = TransportManager(container, config, Registry())

    transport = await manager.transport("database")

    assert isinstance(transport, DatabaseTransport)
    assert transport.connection is scoped_connection
    db.connection.assert_not_called()

    await manager.close()

    scoped_connection.close.assert_not_called()


async def test_database_transport_uses_a_dedicated_connection_for_other_connections(
    serializer: Serializer,
) -> None:
    scoped_connection = MagicMock(spec=AsyncConnection)
    db = _make_database_manager()
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, scoped_connection)
    container.instance(AsyncDatabaseManager, db)
    config = Config(
        {
            "messenger": {
                "transports": {
                    "database": {"driver": "database", "connection": "other"}
                }
            }
        }
    )
    manager = TransportManager(container, config, Registry())

    transport = await manager.transport("database")

    assert isinstance(transport, DatabaseTransport)
    assert transport.connection is not scoped_connection
    db.connection.assert_called_once_with("other")
    transport.connection.start.assert_awaited_once()  # type: ignore[attr-defined]

    await manager.close()

    # The transport owns its dedicated connection
    transport.connection.close.assert_awaited_once()  # type: ignore[attr-defined]


async def test_transport_raises_when_outbox_is_not_configured(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory", "outbox": "missing"},
            },
        }
    )

    with pytest.raises(UnconfiguredTransportError, match="'missing' is not configured"):
        await manager.transport("memory")
