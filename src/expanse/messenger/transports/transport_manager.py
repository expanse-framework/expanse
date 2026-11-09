import asyncio
import logging

from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.receiver import Receiver
from expanse.contracts.messenger.asynchronous.sender import Sender
from expanse.messenger.exceptions import InvalidOutboxTransportError
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.exceptions import UnsupportedTransportOperationError
from expanse.messenger.registry import Registry
from expanse.messenger.transports.memory.queue import MemoryQueue
from expanse.messenger.transports.memory.receiver import MemoryReceiver
from expanse.messenger.transports.memory.sender import MemorySender
from expanse.messenger.transports.sync.sender import SyncSender


logger = logging.getLogger(__name__)


class TransportManager:
    """
    Manage the senders and receivers of the configured transports.

    Senders are used upon dispatch and receivers by workers,
    so they may rely on different resources: the database sender stores messages
    through the scoped connection, so that they are part of its current transaction,
    while the database receiver uses connections of its own.
    """

    def __init__(
        self, container: Container, config: Config, registry: Registry
    ) -> None:
        self._container: Container = container
        self._registry: Registry = registry
        self._config: Config = config
        self._senders: dict[str, Sender] = {}
        self._receivers: dict[str, Receiver] = {}
        self._sender_lock = asyncio.Lock()
        self._receiver_lock = asyncio.Lock()
        # Names of the senders currently being created,
        # used to detect circular outbox configurations.
        self._creating: set[str] = set()

    async def sender(self, name: str | None = None) -> Sender:
        """
        Get the sender of the given transport, used to dispatch messages to it.

        :param name: The name of the transport. Defaults to the default transport.
        """
        if name is None:
            name = self.get_default_transport_name()

        async with self._sender_lock:
            return await self._resolve_sender(name)

    async def _resolve_sender(self, name: str) -> Sender:
        # Resolution is serialized; only recursive calls can encounter a name
        # already being created, so this detects cycles without rejecting peers.
        if name in self._senders:
            return self._senders[name]

        if name in self._creating:
            raise InvalidOutboxTransportError(
                f"Circular outbox configuration detected for transport '{name}'."
            )

        self._creating.add(name)
        try:
            sender = await self._create_sender(name)
            self._senders[name] = sender
            return sender
        finally:
            self._creating.discard(name)

    async def receiver(self, name: str | None = None) -> Receiver:
        """
        Get the receiver of the given transport, used by workers to consume messages.

        Transports with an outbox are consumed directly: messages are relayed
        from the outbox to them.

        :param name: The name of the transport. Defaults to the default transport.
        """
        if name is None:
            name = self.get_default_transport_name()

        async with self._receiver_lock:
            if name not in self._receivers:
                self._receivers[name] = await self._create_receiver(name)
            return self._receivers[name]

    def get_default_transport_name(self) -> str:
        default_transport: str | None = self._config.get("messenger.transport")
        if default_transport is None:
            raise NoDefaultTransportError("No default transport configured.")

        return default_transport

    async def close(self) -> None:
        await asyncio.gather(
            *(sender.close() for sender in self._senders.values()),
            *(receiver.close() for receiver in self._receivers.values()),
        )

    def _transport_config(self, name: str) -> dict[str, Any]:
        transports: dict[str, Any] = self._config.get("messenger.transports", {})
        if name not in transports:
            raise UnconfiguredTransportError(f"Transport '{name}' is not configured.")

        transport_config: dict[str, Any] = transports[name]

        if "driver" not in transport_config:
            raise UnconfiguredTransportError(
                f"Transport '{name}' is missing a driver configuration."
            )

        return transport_config

    async def _create_sender(self, name: str) -> Sender:
        transport_config = self._transport_config(name)

        sender: Sender
        match transport_config["driver"]:
            case "sync":
                sender = SyncSender(self._container, self._registry)
            case "memory":
                receiver = await self.receiver(name)
                assert isinstance(receiver, MemoryReceiver)
                sender = MemorySender(receiver.queue)
            case "database":
                sender = await self._create_database_sender(transport_config)
            case "redis":
                sender = await self._create_redis_sender(transport_config)
            case _:
                raise UnsupportedTransportDriverError(
                    f"Transport '{name}' has an unsupported driver '{transport_config['driver']}'."
                )

        outbox_transport_name = transport_config.get("outbox")
        if not outbox_transport_name:
            return sender

        from expanse.messenger.transports.database.sender import DatabaseSender
        from expanse.messenger.transports.outbox.sender import OutboxSender

        outbox_sender = await self._resolve_sender(outbox_transport_name)

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

    async def _create_receiver(self, name: str) -> Receiver:
        transport_config = self._transport_config(name)

        match transport_config["driver"]:
            case "sync":
                raise UnsupportedTransportOperationError(
                    f"Transport '{name}' handles messages upon dispatch: "
                    "messages cannot be received from it."
                )
            case "memory":
                from expanse.contracts.messenger.serializer import (
                    Serializer as SerializerContract,
                )

                return MemoryReceiver(
                    MemoryQueue(await self._container.get(SerializerContract))
                )
            case "database":
                return await self._create_database_receiver(transport_config)
            case "redis":
                return await self._create_redis_receiver(transport_config)
            case _:
                raise UnsupportedTransportDriverError(
                    f"Transport '{name}' has an unsupported driver '{transport_config['driver']}'."
                )

    async def _create_database_sender(self, config: dict[str, Any]) -> Sender:
        from expanse.contracts.messenger.serializer import (
            Serializer as SerializerContract,
        )
        from expanse.database.asynchronous.connection import AsyncConnection
        from expanse.messenger.transports.database.config import DatabaseTransportConfig
        from expanse.messenger.transports.database.sender import DatabaseSender

        serializer = await self._container.get(SerializerContract)
        transport_config = DatabaseTransportConfig.model_validate(config)

        # Use the scoped connection, so that messages sent through this transport
        # are part of the current transaction of the sessions using it.
        connection = (
            await self._container.get(AsyncConnection)
            if transport_config.connection is None
            else await self._container.get(AsyncConnection, transport_config.connection)
        )

        return DatabaseSender(transport_config, connection, serializer)

    async def _create_database_receiver(self, config: dict[str, Any]) -> Receiver:
        from expanse.contracts.messenger.serializer import (
            Serializer as SerializerContract,
        )
        from expanse.database.database_manager import AsyncDatabaseManager
        from expanse.messenger.transports.database.config import DatabaseTransportConfig
        from expanse.messenger.transports.database.receiver import DatabaseReceiver

        serializer = await self._container.get(SerializerContract)
        transport_config = DatabaseTransportConfig.model_validate(config)

        # Use the engine rather than the scoped connection, so that messages
        # are retrieved and settled independently of the transaction
        # of the message being handled.
        db = await self._container.get(AsyncDatabaseManager)

        return DatabaseReceiver(
            transport_config,
            db.configure_engine(transport_config.connection),
            serializer,
        )

    async def _create_redis_sender(self, raw_config: dict[str, Any]) -> Sender:
        from expanse.contracts.messenger.serializer import (
            Serializer as SerializerContract,
        )
        from expanse.messenger.transports.redis.config import RedisTransportConfig
        from expanse.messenger.transports.redis.sender import RedisSender
        from expanse.redis.asynchronous.redis_manager import RedisManager

        config = RedisTransportConfig.model_validate(raw_config)
        redis = await self._container.get(RedisManager)

        return RedisSender(
            redis.connection(config.connection),
            config,
            await self._container.get(SerializerContract),
        )

    async def _create_redis_receiver(self, raw_config: dict[str, Any]) -> Receiver:
        from expanse.contracts.messenger.serializer import (
            Serializer as SerializerContract,
        )
        from expanse.messenger.transports.redis.config import RedisTransportConfig
        from expanse.messenger.transports.redis.receiver import RedisReceiver
        from expanse.redis.asynchronous.redis_manager import RedisManager

        config = RedisTransportConfig.model_validate(raw_config)
        redis = await self._container.get(RedisManager)

        return RedisReceiver(
            redis.connection(config.connection),
            config,
            await self._container.get(SerializerContract),
        )
