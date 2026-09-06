from abc import ABC
from abc import abstractmethod

from expanse.contracts.rate_limiting.rate_limit import RateLimit


class RateLimiter(ABC):
    @abstractmethod
    async def consume(self, id: str, tokens: int = 1) -> RateLimit: ...

    @abstractmethod
    async def reset(self, id: str) -> None: ...
