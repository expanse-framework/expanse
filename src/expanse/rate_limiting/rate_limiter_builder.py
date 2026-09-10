from collections.abc import Callable

from expanse.rate_limiting.contracts.policy import RateLimitingPolicy


class RateLimiterBuilder:
    def __init__(self) -> None:
        self._policy: RateLimitingPolicy | None = None
        self._id_resolver: Callable[..., str] | None = None

    def sliding_window(self, limit: int, interval: float) -> "RateLimiterBuilder":
        from expanse.rate_limiting.policies.sliding_window.policy import (
            SlidingWindowPolicy,
        )

        self._policy = SlidingWindowPolicy(limit, interval)

        return self

    def by(self, id_resolver: Callable[..., str]) -> "RateLimiterBuilder":
        self._id_resolver = id_resolver

        return self
