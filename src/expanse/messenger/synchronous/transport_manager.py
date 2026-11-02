import logging

from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.contracts.messenger.synchronous.transport import Transport
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.synchronous.transports.memory import MemoryTransport
from expanse.messenger.synchronous.transports.sync import SyncTransport
from expanse.support._concurrency import async_to_sync


logger = logging.getLogger(__name__)


class TransportManager:
    """
    Manage the transports to which the synchronous message bus sends messages.
    """

    def __init__(
        self,
        container: Container,
        config: Config,
        registry: Registry,
        serializer: SerializerContract,
    ) -> None:
        self._container: Container = container
        self._registry: Registry = registry
        self._config: Config = config
        self._serializer: SerializerContract = serializer
        self._transports: dict[str, Transport] = {}
        # Names of the transports currently being created,
        # used to detect circular outbox configurations.
        self._creating: set[str] = set()

    def transport(self, name: str | None = None) -> Transport:
        if name is None:
            name = self.get_default_transport_name()

        if name in self._transports:
            return self._transports[name]

        if name in self._creating:
            raise InvalidOutboxTransportError(
                f"Circular outbox configuration detected for transport '{name}'."
            )

        self._creating.add(name)
        try:
            transport = self._create_transport(name)
        finally:
            self._creating.discard(name)

        self._transports[name] = transport

        return transport

    def get_default_transport_name(self) -> str:
        default_transport: str | None = self._config.get("messenger.transport")
        if default_transport is None:
            raise NoDefaultTransportError("No default transport configured.")

        return default_transport

    def close(self) -> None:
        for transport in self._transports.values():
            transport.close()

    def _create_transport(self, name: str) -> Transport:
        transports: dict[str, Any] = self._config.get("messenger.transports", {})
        if name not in transports:
            raise UnconfiguredTransportError(f"Transport '{name}' is not configured.")

        transport_config = transports[name]

        if "driver" not in transport_config:
            raise UnconfiguredTransportError(
                f"Transport '{name}' is missing a driver configuration."
            )

        transport: Transport
        match transport_config["driver"]:
            case "sync":
                transport = SyncTransport(self._container, self._registry)
            case "memory":
                transport = MemoryTransport(self._serializer)
            case "database":
                transport = self._create_database_transport(transport_config)
            case "redis":
                transport = self._create_redis_transport(transport_config)
            case _:
                raise UnsupportedTransportDriverError(
                    f"Transport '{name}' has an unsupported driver '{transport_config['driver']}'."
                )

        outbox_transport_name = transport_config.get("outbox")
        if not outbox_transport_name:
            return transport

        from expanse.messenger.synchronous.transports.database import DatabaseTransport
        from expanse.messenger.synchronous.transports.outbox import OutboxTransport

        outbox_transport = self.transport(outbox_transport_name)

        if not isinstance(outbox_transport, DatabaseTransport):
            raise InvalidOutboxTransportError(
                "The outbox transport must be a database transport."
            )

        logger.debug(
            "Creating outbox transport",
            extra={
                "target_transport": name,
                "outbox_transport": outbox_transport_name,
            },
        )

        return OutboxTransport(
            target_transport=transport,
            outbox_transport=outbox_transport,
            target_transport_name=name,
        )

    def _create_database_transport(self, config: dict[str, Any]) -> Transport:
        from expanse.database.synchronous.connection import Connection
        from expanse.messenger.synchronous.transports.database import DatabaseTransport
        from expanse.messenger.transports.database.config import DatabaseTransportConfig

        transport_config = DatabaseTransportConfig.model_validate(config)

        # Use the scoped connection, so that messages sent through this transport
        # are part of the current transaction of the sessions using it.
        get = async_to_sync(self._container.get)
        connection: Connection = (
            get(Connection)
            if transport_config.connection is None
            else get(Connection, transport_config.connection)
        )

        return DatabaseTransport(transport_config, connection, self._serializer)

    def _create_redis_transport(self, raw_config: dict[str, Any]) -> Transport:
        from expanse.messenger.synchronous.transports.redis import RedisTransport
        from expanse.messenger.transports.redis.config import RedisTransportConfig
        from expanse.redis.synchronous.redis_manager import RedisManager

        config = RedisTransportConfig.model_validate(raw_config)
        redis = async_to_sync(self._container.get)(RedisManager)

        return RedisTransport(
            redis.connection(config.connection), config, self._serializer
        )
