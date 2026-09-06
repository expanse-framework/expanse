from math import floor
from time import time
from typing import Self
from typing import final
from typing import override

import msgspec
import whenever

from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.contracts.rate_limiting.rate_limit import RateLimit
from expanse.contracts.rate_limiting.rate_limiter import RateLimiter
from expanse.rate_limiting.exceptions import TokenConsumptionOverLimitError
from expanse.support.duration import SingleUnitDuration


class SlidingWindowRateLimiter(RateLimiter):
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

        async with self._cache.lock(f"__expanse__:rate-limit:lock:{id}"):
            window_data: bytes | None = await self._cache.get(
                f"__expanse__:rate-limit:{id}"
            )
            if window_data is None:
                window = Window(id, self._interval)
            else:
                window = Window.decode(window_data)

                if window.is_expired():
                    window = Window.from_previous_window(
                        window, interval=self._interval
                    )

            now = time()
            hit_count = window.hit_count
            available_tokens = self._limit - hit_count

            if tokens == 0:
                reset_duration = window.calculate_time_for_tokens(
                    self._limit, window.hit_count
                )
                reset_time = whenever.Instant.from_timestamp(
                    now if available_tokens else now + reset_duration
                )
                return RateLimit(available_tokens, reset_time, True, self._limit)

            if available_tokens >= tokens:
                window.add(tokens)

                retry_after = now
                if available_tokens == tokens:
                    retry_after += window.calculate_time_for_tokens(
                        self._limit, window.hit_count
                    )

                rate_limit = RateLimit(
                    self._limit - window.hit_count,
                    whenever.Instant.from_timestamp(retry_after),
                    True,
                    self._limit,
                )

                await self._cache.set(
                    f"__expanse__:rate-limit:{id}",
                    window.encode(),
                    ttl=window.expires_in,
                )

                return rate_limit
            else:
                wait_duration = window.calculate_time_for_tokens(self._limit, tokens)

                return RateLimit(
                    self._limit - window.hit_count,
                    whenever.Instant.from_timestamp(now + wait_duration),
                    False,
                    self._limit,
                )

    @override
    async def reset(self, id: str) -> None:
        async with self._cache.lock(f"__expanse__:rate-limit:lock:{id}"):
            await self._cache.delete(f"__expanse__:rate-limit:{id}")


@final
class Window:
    __slots__ = (
        "_ends_at",
        "_hit_count",
        "_hit_count_for_last_window",
        "_id",
        "_interval",
    )

    def __init__(self, id: str, interval: int) -> None:
        self._id: str = id
        self._interval: int = interval
        self._ends_at = time() + self._interval
        self._hit_count: int = 0
        self._hit_count_for_last_window: int = 0

    @property
    def expires_in(self) -> int:
        return int(self._ends_at + self._interval - time())

    @property
    def hit_count(self) -> int:
        return self._hit_count

    def is_expired(self) -> bool:
        return time() > self._ends_at

    def calculate_time_for_tokens(self, max_size: int, tokens: int) -> float:
        remaining = max_size - self.hit_count
        if remaining >= tokens:
            return 0

        now = time()
        window_start = self._ends_at - self._interval
        elapsed_time = now - window_start
        elapsed_window = min(elapsed_time / self._interval, 1)
        releasable = max(
            1, max_size - floor(self._hit_count_for_last_window * (1 - elapsed_window))
        )
        remaining_window = self._interval - elapsed_time
        needed = tokens - remaining

        if releasable >= needed:
            return needed * (remaining_window / max(1, releasable))

        return (self._ends_at - now) + (needed - releasable) * (
            self._interval / max_size
        )

    def add(self, hits: int = 0) -> None:
        self._hit_count += hits

    @classmethod
    def from_previous_window(cls, previous_window: "Window", interval: int) -> Self:
        window = cls(id=previous_window._id, interval=interval)
        ends_at = previous_window._ends_at + interval

        if time() < ends_at:
            window._hit_count_for_last_window = window.hit_count
            window._ends_at = ends_at

        return window

    def encode(self) -> bytes:
        return msgspec.json.encode(
            {
                "id": self._id,
                "interval": self._interval,
                "ends_at": self._ends_at,
                "hit_count": self._hit_count,
                "hit_count_for_last_window": self._hit_count_for_last_window,
            }
        )

    @classmethod
    def decode(cls, data: bytes) -> Self:
        decoded = msgspec.json.decode(data)
        window = cls(id=decoded["id"], interval=decoded["interval"])
        window._ends_at = decoded["ends_at"]
        window._hit_count = decoded["hit_count"]
        window._hit_count_for_last_window = decoded["hit_count_for_last_window"]
        return window


__all__ = ["SlidingWindowRateLimiter"]
