import os

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.transports.memory.transport import MemoryTransport
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
