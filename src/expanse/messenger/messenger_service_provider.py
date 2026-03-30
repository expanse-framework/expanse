from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.message_bus import (
    MessageBus as MessageBusContract,
)
from expanse.contracts.messenger.synchronous.message_bus import (
    MessageBus as SyncMessageBusContract,
)
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal
    from expanse.database.asynchronous.session import AsyncSession
    from expanse.database.synchronous.session import Session


class MessengerServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.messenger.registry import Registry
        from expanse.messenger.serializer import Serializer

        self._container.singleton(Registry)
        self._container.singleton(Serializer)
        self._container.scoped(TransportManager)
        self._container.scoped(MiddlewareStack)
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

    async def _create_message_bus(
        self,
        transport_manager: TransportManager,
        container: Container,
        stack: MiddlewareStack,
    ) -> MessageBusContract:
        from expanse.messenger.asynchronous.message_bus import MessageBus
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        return TransactionalMessageBus(MessageBus(transport_manager, container, stack))

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
        from expanse.database.session import Session
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        if not isinstance(bus, TransactionalMessageBus):
            return

        if container.resolved(Session):
            bus.attach_session(await container.get(Session))

    async def _attach_resolved_session_to_transactional_bus(
        self, session: "Session | AsyncSession", bus: MessageBusContract
    ) -> None:
        from expanse.messenger.asynchronous.transactional_message_bus import (
            TransactionalMessageBus,
        )

        if not isinstance(bus, TransactionalMessageBus):
            return

        bus.attach_session(session)
