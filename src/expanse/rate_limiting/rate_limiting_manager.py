from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
from expanse.rate_limiting.exceptions import UnconfiguredRateLimiterError
from expanse.rate_limiting.exceptions import UnsupportedRateLimiterPolicyError


class RateLimitingManager:
    def __init__(self, config: Config, container: Container) -> None:
        self._config: Config = config
        self._container: Container = container
        self._limiters: dict[str, RateLimiter] = {}

    async def limiter(self, name: str) -> RateLimiter:
        if name in self._limiters:
            return self._limiters[name]

        limiter = await self._create_limiter(name)
        self._limiters[name] = limiter

        return limiter

    async def add(self, name: str, limiter: RateLimiter) -> None:
        self._limiters[name] = limiter

    async def _create_limiter(self, name: str) -> RateLimiter:
        limiters: dict[str, dict[str, Any]] = self._config.get(
            "rate_limiting.limiters", {}
        )
        if name not in limiters:
            raise UnconfiguredRateLimiterError(
                f"Rate limiter '{name}' is not configured."
            )

        limiter_config = limiters[name]

        if "policy" not in limiter_config:
            raise UnconfiguredRateLimiterError(
                f"Transport '{name}' is missing a policy configuration."
            )

        match limiter_config["policy"]:
            case "sliding_window":
                return await self._create_sliding_window_limiter(limiter_config)
            case _:
                raise UnsupportedRateLimiterPolicyError(
                    f"Rate limiter '{name}' has an unsupported policy '{limiter_config['policy']}'."
                )

    async def _create_sliding_window_limiter(
        self, raw_config: dict[str, Any]
    ) -> RateLimiter:
        from expanse.cache.asynchronous.cache_manager import CacheManager
        from expanse.rate_limiting.rate_limiters.sliding_window.config import (
            SlidingWindowRateLimiterConfig,
        )
        from expanse.rate_limiting.rate_limiters.sliding_window.rate_limiter import (
            SlidingWindowRateLimiter,
        )

        config = SlidingWindowRateLimiterConfig.model_validate(raw_config)
        cache_manager = await self._container.get(CacheManager)
        cache = await cache_manager.cache(config.cache_store)

        return SlidingWindowRateLimiter(config.limit, config.interval, cache)
