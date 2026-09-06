from abc import ABC
from abc import abstractmethod


class RateLimiterStorage(ABC):
    @abstractmethod
    async def save(self) -> None: ...

    @abstractmethod
    async def fetch(self) -> None: ...

    @abstractmethod
    async def delete(self, state_id: str) -> None: ...
