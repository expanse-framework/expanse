from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.contracts.messenger.transports.transport_manager import (
    TransportManager as TransportManagerContract,
)


class TransportManager(TransportManagerContract):
    def __init__(self, manager: TransportManagerContract) -> None:
        self._manager: TransportManagerContract = manager

    async def transport(self, name: str | None = None) -> Transport:
        return await self._manager.transport(name)
