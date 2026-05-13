from abc import ABC
from abc import abstractmethod

from expanse.contracts.messenger.asynchronous.transport import Transport


class TransportManager(ABC):
    @abstractmethod
    async def transport(self, name: str | None = None) -> Transport: ...
