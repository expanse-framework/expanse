from math import floor
from time import time
from typing import override

import whenever

from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.contracts.rate_limiting.rate_limit import RateLimit
from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
from expanse.rate_limiting.exceptions import TokenConsumptionOverLimitError
from expanse.support.duration import SingleUnitDuration


class SlidingWindowRateLimiter(RateLimiter):
    _WINDOW_KEY_FORMAT: str = "__expanse__:rate-limit:{id}:sliding:{window}"
    _LOCK_KEY_FORMAT: str = "__expanse__:rate-limit:lock:{id}"

    def __init__(self, limit: int, interval: SingleUnitDuration, cache: Cache) -> None:
        self._limit: int = limit
        self._interval: int = interval.to_seconds()
        self._cache: Cache = cache

    @override
    async def consume(self, id: str, tokens: int = 1) -> RateLimit:
        if tokens > self._limit:
            raise TokenConsumptionOverLimitError(
                f"The number of tokens consumed ({tokens}) cannot be greater than the limit {self._limit}"
            )

        async with self._cache.lock(self._LOCK_KEY_FORMAT.format(id=id)):
            now = floor(time())
            current_window, previous_window = self._calculate_windows()
            elapsed = now - current_window
            weight = (self._interval - elapsed) / self._interval

            previous_key = self._WINDOW_KEY_FORMAT.format(id=id, window=previous_window)
            current_key = self._WINDOW_KEY_FORMAT.format(id=id, window=current_window)

            window_data = await self._cache.get_many([previous_key, current_key])

            previous_token_count = window_data.get(previous_key, 0) or 0
            current_token_count = window_data.get(current_key, 0) or 0

            estimated = floor(previous_token_count * weight) + current_token_count

            if estimated + tokens > self._limit:
                return RateLimit(
                    0,
                    whenever.Instant.from_timestamp(current_window + self._interval),
                    False,
                    self._limit,
                )

            await self._cache.set(
                current_key, current_token_count + tokens, ttl=self._interval * 2
            )

            return RateLimit(
                max(0, self._limit - (estimated + tokens)),
                whenever.Instant.from_timestamp(current_window + self._interval),
                True,
                self._limit,
            )

    @override
    async def reset(self, id: str) -> None:
        async with self._cache.lock(self._LOCK_KEY_FORMAT.format(id=id)):
            await self._cache.delete_many(
                [
                    self._WINDOW_KEY_FORMAT.format(id=id, window=w)
                    for w in self._calculate_windows()
                ]
            )

    def _calculate_windows(self) -> tuple[int, int]:
        now = floor(time())
        current_window = floor(now / self._interval) * self._interval
        previous_window = current_window - self._interval

        return current_window, previous_window


__all__ = ["SlidingWindowRateLimiter"]
