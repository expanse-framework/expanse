import asyncio
import os

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.sender import Sender
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.database.asynchronous.connection import AsyncConnection
from expanse.database.database_manager import AsyncDatabaseManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.exceptions import UnsupportedTransportOperationError
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.stamps.outbox import OutboxStamp
from expanse.messenger.transports.database.receiver import DatabaseReceiver
from expanse.messenger.transports.database.sender import DatabaseSender
from expanse.messenger.transports.memory.receiver import MemoryReceiver
from expanse.messenger.transports.memory.sender import MemorySender
from expanse.messenger.transports.outbox.sender import OutboxSender
from expanse.messenger.transports.redis.receiver import RedisReceiver
from expanse.messenger.transports.redis.sender import RedisSender
from expanse.messenger.transports.sync.sender import SyncSender
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
        container.instance(AsyncDatabaseManager, MagicMock(spec=AsyncDatabaseManager))

        return TransportManager(container, config, registry)

    return _make_manager


async def test_sender_returns_the_sender_of_the_default_transport(
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

    sender = await manager.sender()

    assert isinstance(sender, MemorySender)


async def test_sender_returns_the_sender_of_the_named_transport(
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

    sender = await manager.sender("sync")

    assert isinstance(sender, SyncSender)


async def test_sender_caches_sender_instance(
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

    first = await manager.sender("memory")
    second = await manager.sender("memory")

    assert first is second


async def test_sender_creates_memory_sender(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
            },
        }
    )

    sender = await manager.sender("memory")

    assert isinstance(sender, MemorySender)


async def test_sender_creates_sync_sender(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "sync": {"driver": "sync"},
            },
        }
    )

    sender = await manager.sender("sync")

    assert isinstance(sender, SyncSender)


async def test_sender_creates_redis_sender(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "sync": {"driver": "redis", "connection": "default"},
            },
        }
    )

    sender = await manager.sender("sync")

    assert isinstance(sender, RedisSender)


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


async def test_sender_raises_for_unconfigured_transport(
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
        await manager.sender("unknown")


async def test_sender_raises_when_driver_missing(
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
        await manager.sender("broken")


async def test_sender_raises_for_unsupported_driver(
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
        await manager.sender("custom")


async def test_sender_without_name_raises_when_no_default(
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
        await manager.sender()


async def test_senders_of_different_transports_are_cached_independently(
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

    memory = await manager.sender("memory")
    sync = await manager.sender("sync")

    assert isinstance(memory, MemorySender)
    assert isinstance(sync, SyncSender)
    assert memory is not sync


async def test_sender_wraps_transports_configured_with_an_outbox(
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

    sender = await manager.sender("memory")

    assert isinstance(sender, OutboxSender)
    assert isinstance(sender.target_sender, MemorySender)


async def test_outbox_sender_stores_messages_in_the_configured_outbox(
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

    sender = await manager.sender("memory")
    outbox = await manager.sender("outbox")
    assert isinstance(outbox, DatabaseSender)

    sent: list[Envelope] = []

    async def send(envelope: Envelope) -> Envelope:
        sent.append(envelope)

        return envelope

    outbox.send = send  # type: ignore[method-assign]

    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    assert len(sent) == 1
    assert sent[0].stamp(OutboxStamp) == OutboxStamp(target_transport_name="memory")


@pytest.mark.parametrize("outbox", [None, ""])
async def test_sender_is_not_wrapped_when_outbox_is_empty(
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

    sender = await manager.sender("memory")

    assert isinstance(sender, MemorySender)


async def test_sender_raises_when_outbox_is_not_a_database_transport(
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
        await manager.sender("memory")


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
async def test_sender_raises_on_circular_outbox_configuration(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
    transports: dict[str, Any],
) -> None:
    manager = make_manager({"transports": transports})

    with pytest.raises(InvalidOutboxTransportError, match="Circular outbox"):
        await manager.sender(next(iter(transports)))


async def test_database_sender_uses_the_scoped_connection(
    serializer: Serializer,
) -> None:
    connection = MagicMock(spec=AsyncConnection)
    container = Container()
    container.instance(SerializerContract, serializer)
    container.instance(AsyncConnection, connection)
    config = Config({"messenger": {"transports": {"database": {"driver": "database"}}}})
    manager = TransportManager(container, config, Registry())

    sender = await manager.sender("database")

    assert isinstance(sender, DatabaseSender)
    assert sender.connection is connection


async def test_database_sender_uses_the_scoped_connection_of_the_configured_connection(
    serializer: Serializer,
) -> None:
    default_connection = MagicMock(spec=AsyncConnection)
    other_connection = MagicMock(spec=AsyncConnection)
    container = Container()
    container.instance(SerializerContract, serializer)

    def make_connection(name: str | None = None) -> AsyncConnection:
        return other_connection if name == "other" else default_connection

    container.singleton(AsyncConnection, make_connection)
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

    sender = await manager.sender("database")

    assert isinstance(sender, DatabaseSender)
    assert sender.connection is other_connection


async def test_sender_raises_when_outbox_is_not_configured(
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
        await manager.sender("memory")


async def test_receiver_returns_the_receiver_of_the_default_transport(
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

    receiver = await manager.receiver()

    assert isinstance(receiver, MemoryReceiver)


async def test_receiver_caches_receiver_instance(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({"transports": {"memory": {"driver": "memory"}}})

    assert await manager.receiver("memory") is await manager.receiver("memory")


async def test_memory_sender_and_receiver_share_the_same_queue(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
                "other": {"driver": "memory"},
            }
        }
    )

    sender = await manager.sender("memory")
    receiver = await manager.receiver("memory")
    other_receiver = await manager.receiver("other")
    assert isinstance(sender, MemorySender)
    assert isinstance(receiver, MemoryReceiver)
    assert isinstance(other_receiver, MemoryReceiver)

    await sender.send(Envelope.wrap(FooMessage(value="hello")))

    received = [envelope.open() async for envelope in receiver.receive()]

    assert received == [FooMessage(value="hello")]
    assert [envelope async for envelope in other_receiver.receive()] == []


async def test_receiver_creates_redis_receiver(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {"transports": {"redis": {"driver": "redis", "connection": "default"}}}
    )

    assert isinstance(await manager.receiver("redis"), RedisReceiver)


async def test_receiver_raises_for_the_sync_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({"transports": {"sync": {"driver": "sync"}}})

    with pytest.raises(
        UnsupportedTransportOperationError, match="cannot be received from"
    ):
        await manager.receiver("sync")


async def test_receiver_of_a_transport_with_an_outbox_is_the_receiver_of_the_transport(
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

    sender = await manager.sender("memory")
    receiver = await manager.receiver("memory")
    assert isinstance(sender, OutboxSender)
    assert isinstance(receiver, MemoryReceiver)

    # Messages redelivered through the outbox sender reach the receiver directly
    await sender.send(
        Envelope.wrap(FooMessage(value="hello")).with_stamps(
            OutboxStamp(target_transport_name="memory")
        )
    )

    received = [envelope.open() async for envelope in receiver.receive()]

    assert received == [FooMessage(value="hello")]


async def test_receiver_raises_for_unconfigured_transport(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({"transports": {}})

    with pytest.raises(UnconfiguredTransportError, match="'unknown' is not configured"):
        await manager.receiver("unknown")


async def test_receiver_raises_for_unsupported_driver(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager({"transports": {"custom": {"driver": "invalid"}}})

    with pytest.raises(
        UnsupportedTransportDriverError, match="unsupported driver 'invalid'"
    ):
        await manager.receiver("custom")


@pytest.mark.parametrize("connection_name", [None, "other"])
async def test_database_receiver_uses_the_engine_rather_than_the_scoped_connection(
    serializer: Serializer, connection_name: str | None
) -> None:
    requested_connections: list[str | None] = []

    def make_connection(name: str | None = None) -> AsyncConnection:
        requested_connections.append(name)

        return MagicMock(spec=AsyncConnection)

    engine = MagicMock()
    db = MagicMock(spec=AsyncDatabaseManager)
    db.configure_engine.return_value = engine
    container = Container()
    container.instance(SerializerContract, serializer)
    container.singleton(AsyncConnection, make_connection)
    container.instance(AsyncDatabaseManager, db)
    config = Config(
        {
            "messenger": {
                "transports": {
                    "database": {"driver": "database", "connection": connection_name}
                }
            }
        }
    )
    manager = TransportManager(container, config, Registry())

    receiver = await manager.receiver("database")

    assert isinstance(receiver, DatabaseReceiver)
    assert receiver.engine is engine
    db.configure_engine.assert_called_once_with(connection_name)
    assert requested_connections == []


async def test_close_closes_senders_and_receivers(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
) -> None:
    manager = make_manager(
        {
            "transports": {
                "memory": {"driver": "memory"},
                "other": {"driver": "memory"},
            }
        }
    )

    sender = await manager.sender("memory")
    receiver = await manager.receiver("other")
    assert isinstance(sender, MemorySender)
    assert isinstance(receiver, MemoryReceiver)

    await sender.send(Envelope.wrap(FooMessage(value="hello")))
    await (await manager.sender("other")).send(Envelope.wrap(FooMessage(value="hi")))

    await manager.close()

    assert sender.sent == []
    assert receiver.queue.sent == []


async def test_concurrent_sender_initialization_waits_for_the_same_sender(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = make_manager({"transports": {"memory": {"driver": "memory"}}})
    started = asyncio.Event()
    release = asyncio.Event()
    create = manager._create_sender

    async def slow_create(name: str) -> Sender:
        started.set()
        await release.wait()
        return await create(name)

    factory = AsyncMock(side_effect=slow_create)
    monkeypatch.setattr(manager, "_create_sender", factory)
    first = asyncio.create_task(manager.sender("memory"))
    await started.wait()
    second = asyncio.create_task(manager.sender("memory"))
    await asyncio.sleep(0)
    release.set()
    senders = await asyncio.gather(first, second)
    assert senders[0] is senders[1]
    factory.assert_awaited_once_with("memory")


async def test_sender_initialization_can_be_retried_after_failure(
    make_manager: Callable[[dict[str, Any] | None], TransportManager],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = make_manager({"transports": {"memory": {"driver": "memory"}}})
    create = manager._create_sender
    factory = AsyncMock(side_effect=RuntimeError("initialization failed"))
    monkeypatch.setattr(manager, "_create_sender", factory)
    with pytest.raises(RuntimeError, match="initialization failed"):
        await manager.sender("memory")
    monkeypatch.setattr(manager, "_create_sender", create)
    assert isinstance(await manager.sender("memory"), MemorySender)
