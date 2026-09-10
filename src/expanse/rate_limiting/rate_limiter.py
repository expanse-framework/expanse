from typing import override

from expanse.contracts.rate_limiting.rate_limit import RateLimit
from expanse.contracts.rate_limiting.rate_limiter import (
    RateLimiter as RateLimiterContract,
)
from expanse.rate_limiting.contracts.policy import RateLimitingPolicy


class RateLimiter(RateLimiterContract):
    def __init__(self, name: str, policy: RateLimitingPolicy) -> None:
        self._name: str = name
        self._policy: RateLimitingPolicy = policy
        self._id_resolver: str | None

    @property
    def name(self) -> str:
        return self._name

    @override
    async def consume(self, tokens: int = 1) -> RateLimit:
        return await super().consume(id, tokens)

    @override
    async def reset(self, id: str) -> None:
        return await super().reset(id)
