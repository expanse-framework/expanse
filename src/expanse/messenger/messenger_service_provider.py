from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal
    from expanse.messenger.asynchronous.message_bus import MessageBus


class MessengerServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.contracts.messenger.asynchronous.message_bus import (
            MessageBus as MessageBusContract,
        )
        from expanse.messenger.registry import Registry

        self._container.singleton(Registry)
        self._container.scoped(TransportManager)
        self._container.scoped(MiddlewareStack)
        self._container.scoped(MessageBusContract, self._create_message_bus)

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _create_message_bus(
        self,
        transport_manager: TransportManager,
        container: Container,
        stack: MiddlewareStack,
    ) -> "MessageBus":
        from expanse.messenger.asynchronous.message_bus import MessageBus

        return MessageBus(transport_manager, container, stack)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
