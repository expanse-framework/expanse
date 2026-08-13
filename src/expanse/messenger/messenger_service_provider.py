from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.encryption.signer import Signer
from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as SyncMessageBusContract,
)
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.retry.retry_strategy_manager import RetryStrategyManager
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.messenger.trusted_collection import TrustedCollection
from expanse.serialization.serialization_manager import SerializationManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.contracts.messenger.serializer import Serializer as SerializerContract
    from expanse.core.console.portal import Portal
    from expanse.database.asynchronous.session import AsyncSession
    from expanse.database.synchronous.session import Session


class MessengerServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.contracts.messenger.serializer import (
            Serializer as SerializerContract,
        )
        from expanse.messenger.registry import Registry

        self._container.singleton(Registry)
        self._container.singleton(TrustedCollection)
        self._container.singleton(SerializationManager)
        self._container.singleton(SerializerContract, self._create_serializer)
        self._container.singleton(RetryStrategyManager)
        self._container.singleton(MiddlewareStack)
        self._container.scoped(TransportManager, self._create_transport_manager)
        self._container.scoped(MessageBusContract, self._create_message_bus)
        self._container.scoped(SyncMessageBusContract, self._create_sync_message_bus)

    async def boot(self) -> None:
        from expanse.contracts.messenger.asynchronous.message_bus import (
            MessageBus as MessageBusContract,
        )
        from expanse.core.console.portal import Portal
        from expanse.database.asynchronous.session import AsyncSession
        from expanse.database.synchronous.session import Session

        await self._container.on_resolved(Portal, self._register_command_path)
        await self._container.on_resolved(
            MessageBusContract, self._attach_session_to_transactional_bus
        )
        await self._container.on_resolved(
            Session, self._attach_resolved_session_to_transactional_bus
        )
        await self._container.on_resolved(
            AsyncSession, self._attach_resolved_session_to_transactional_bus
        )
        await self._container.on_resolved(
            SerializationManager, self._register_serializers
        )

    async def _create_serializer(self, container: Container) -> "SerializerContract":
        from expanse.messenger.serializers.serializer import Serializer

        config = await container.get(Config)
        messenger_config: dict[str, Any] = config.get("messenger", {})

        serializer: SerializerContract

        serializer = Serializer(await container.get(SerializationManager))

        sign: bool = messenger_config.get("sign", True)
        if sign:
            from expanse.messenger.serializers.signing_serializer import (
                SigningSerializer,
            )

            return SigningSerializer(serializer, await container.get(Signer))

        return serializer

    async def _create_transport_manager(
        self, container: Container, config: Config, registry: Registry
    ) -> AsyncGenerator[TransportManager, None]:
        manager = TransportManager(container, config, registry)

        yield manager

        await manager.close()

    async def _create_message_bus(
        self,
        transport_manager: TransportManager,
        container: Container,
        stack: MiddlewareStack,
    ) -> AsyncGenerator[MessageBusContract]:
        from expanse.messenger.asynchronous.message_bus import MessageBus
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        bus = TransactionalMessageBus(MessageBus(transport_manager, container, stack))

        yield bus

        bus.close()

    async def _create_sync_message_bus(
        self,
        async_bus: MessageBusContract,
    ) -> SyncMessageBusContract:
        from expanse.messenger.synchronous.message_bus import MessageBus

        return MessageBus(async_bus)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def _attach_session_to_transactional_bus(
        self,
        bus: MessageBusContract,
        container: Container,
    ) -> None:
        from expanse.database.session import AsyncSession
        from expanse.database.session import Session
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        if not isinstance(bus, TransactionalMessageBus):
            return

        if container.resolved(Session):
            bus.attach_session(await container.get(Session))

        if container.resolved(AsyncSession):
            bus.attach_session(await container.get(AsyncSession))

    async def _attach_resolved_session_to_transactional_bus(
        self, session: "Session | AsyncSession", container: Container
    ) -> None:
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        if not container.resolved(MessageBusContract):
            return

        bus = await container.get(MessageBusContract)

        if not isinstance(bus, TransactionalMessageBus):
            return

        bus.attach_session(session)

    async def _register_serializers(
        self, serialization_manager: SerializationManager, container: Container
    ) -> None:
        from expanse.serialization.serializers.dataclass import DataclassSerializer
        from expanse.serialization.serializers.msgspec import MsgSpecSerializer
        from expanse.serialization.serializers.pickle import PickleSerializer
        from expanse.serialization.serializers.pydantic import PydanticSerializer

        config = await container.get(Config)
        is_strict = config.get("messenger.strict", False)

        trusted_collection = await container.get(TrustedCollection)

        serialization_manager.register_serializer(
            DataclassSerializer().restrict(trusted_collection.class_names)
            if is_strict
            else DataclassSerializer()
        )
        serialization_manager.register_serializer(
            PydanticSerializer().restrict(trusted_collection.class_names)
            if is_strict
            else PydanticSerializer()
        )
        serialization_manager.register_serializer(
            MsgSpecSerializer().restrict(trusted_collection.class_names)
            if is_strict
            else MsgSpecSerializer()
        )
        serialization_manager.register_serializer(
            PickleSerializer().restrict(trusted_collection.class_names)
        )
