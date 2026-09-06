from typing import override

from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
from expanse.rate_limiting.rate_limiting_manager import RateLimitingManager
from expanse.support.service_provider import ServiceProvider


class RateLimitingServiceProvider(ServiceProvider):
    @override
    async def register(self) -> None:
        from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
        from expanse.rate_limiting.rate_limiting_manager import RateLimitingManager

        self._container.singleton(RateLimitingManager)
        self._container.singleton(RateLimiter, self._get_rate_limiter)

    async def _get_rate_limiter(
        self, manager: RateLimitingManager, name: str, /
    ) -> RateLimiter:
        return await manager.limiter(name)
