from typing import override

from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
from expanse.rate_limiting.rate_limiting import RateLimiting
from expanse.support.service_provider import ServiceProvider


class RateLimitingServiceProvider(ServiceProvider):
    @override
    async def register(self) -> None:
        from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
        from expanse.rate_limiting.rate_limiting import RateLimiting

        self._container.singleton(RateLimiting)
        self._container.singleton(RateLimiter, self._get_rate_limiter)

    async def _get_rate_limiter(
        self, manager: RateLimiting, name: str, /
    ) -> RateLimiter:
        return await manager.limiter(name)
