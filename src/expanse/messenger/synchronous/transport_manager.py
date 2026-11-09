import logging

from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.contracts.messenger.synchronous.sender import Sender
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.synchronous.transports.memory import MemorySender
from expanse.messenger.synchronous.transports.sync import SyncSender
from expanse.support._concurrency import async_to_sync


logger = logging.getLogger(__name__)


class TransportManager:
    """
    Manage the senders to which the synchronous message bus sends messages.
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
        self._senders: dict[str, Sender] = {}
        # Names of the transports currently being created,
        # used to detect circular outbox configurations.
        self._creating: set[str] = set()

    def sender(self, name: str | None = None) -> Sender:
        if name is None:
            name = self.get_default_transport_name()

        if name in self._senders:
            return self._senders[name]

        if name in self._creating:
            raise InvalidOutboxTransportError(
                f"Circular outbox configuration detected for transport '{name}'."
            )

        self._creating.add(name)
        try:
            sender = self._create_sender(name)
        finally:
            self._creating.discard(name)

        self._senders[name] = sender

        return sender

    def get_default_transport_name(self) -> str:
        default_transport: str | None = self._config.get("messenger.transport")
        if default_transport is None:
            raise NoDefaultTransportError("No default transport configured.")

        return default_transport

    def close(self) -> None:
        for sender in self._senders.values():
            sender.close()

    def _create_sender(self, name: str) -> Sender:
        transports: dict[str, Any] = self._config.get("messenger.transports", {})
        if name not in transports:
            raise UnconfiguredTransportError(f"Transport '{name}' is not configured.")

        transport_config = transports[name]

        if "driver" not in transport_config:
            raise UnconfiguredTransportError(
                f"Transport '{name}' is missing a driver configuration."
            )

        sender: Sender
        match transport_config["driver"]:
            case "sync":
                sender = SyncSender(self._container, self._registry)
            case "memory":
                sender = MemorySender(self._serializer)
            case "database":
                sender = self._create_database_sender(transport_config)
            case "redis":
                sender = self._create_redis_sender(transport_config)
            case _:
                raise UnsupportedTransportDriverError(
                    f"Transport '{name}' has an unsupported driver '{transport_config['driver']}'."
                )

        outbox_transport_name = transport_config.get("outbox")
        if not outbox_transport_name:
            return sender

        from expanse.messenger.synchronous.transports.database import DatabaseSender
        from expanse.messenger.synchronous.transports.outbox import OutboxSender

        outbox_sender = self.sender(outbox_transport_name)

        if not isinstance(outbox_sender, DatabaseSender):
            raise InvalidOutboxTransportError(
                "The outbox transport must be a database transport."
            )

        logger.debug(
            "Creating outbox sender",
            extra={
                "target_transport": name,
                "outbox_transport": outbox_transport_name,
            },
        )

        return OutboxSender(
            target_sender=sender,
            outbox_sender=outbox_sender,
            target_transport_name=name,
        )

    def _create_database_sender(self, config: dict[str, Any]) -> Sender:
        from expanse.database.synchronous.connection import Connection
        from expanse.messenger.synchronous.transports.database import DatabaseSender
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

        return DatabaseSender(transport_config, connection, self._serializer)

    def _create_redis_sender(self, raw_config: dict[str, Any]) -> Sender:
        from expanse.messenger.synchronous.transports.redis import RedisSender
        from expanse.messenger.transports.redis.config import RedisTransportConfig
        from expanse.redis.synchronous.redis_manager import RedisManager

        config = RedisTransportConfig.model_validate(raw_config)
        redis = async_to_sync(self._container.get)(RedisManager)

        return RedisSender(
            redis.connection(config.connection), config, self._serializer
        )
