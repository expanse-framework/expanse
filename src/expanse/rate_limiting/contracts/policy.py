from abc import ABC
from abc import abstractmethod

from expanse.contracts.rate_limiting.rate_limit import RateLimit


class RateLimitingPolicy(ABC):
    @abstractmethod
    async def consume(self, id: str, tokens: int = 1) -> RateLimit:
        """
        Consume tokens from the rate limit for the given id.

        :param id: The unique identifier for the rate limit (e.g., user ID, IP address).
        :param tokens: The number of tokens to consume. Defaults to 1.

        :return: A RateLimit object representing the current state of the rate limit.
        """

    @abstractmethod
    async def reset(self, id: str) -> None:
        """
        Reset the rate limit for the given id.

        :param id: The unique identifier for the rate limit (e.g., user ID, IP address).
        """
