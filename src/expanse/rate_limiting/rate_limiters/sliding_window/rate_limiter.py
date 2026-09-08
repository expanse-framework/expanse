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
            available_tokens = max(0, self._limit - window.hit_count)

            if tokens == 0:
                # No token is consumed, so the request is always accepted and the
                # retry time is the time at which the next token will be available.
                retry_after = now + window.calculate_time_for_tokens(self._limit, 1)

                return RateLimit(
                    available_tokens,
                    whenever.Instant.from_timestamp(retry_after),
                    True,
                    self._limit,
                )

            if available_tokens >= tokens:
                window.add(tokens)

                # The retry time is the time at which the next token will be
                # available, which is now as long as the limit is not reached.
                retry_after = now + window.calculate_time_for_tokens(self._limit, 1)

                rate_limit = RateLimit(
                    max(0, self._limit - window.hit_count),
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
                    available_tokens,
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
        """
        The number of hits recorded in the window.

        The hits of the previous window are accounted for, proportionally to the
        part of it that still overlaps the current window, which is what makes
        the window slide.
        """
        return floor(
            self._hit_count_for_last_window * (1 - self._elapsed_window_ratio())
            + self._hit_count
        )

    def is_expired(self) -> bool:
        return time() > self._ends_at

    def calculate_time_for_tokens(self, max_size: int, tokens: int) -> float:
        remaining = max_size - self.hit_count
        if remaining >= tokens:
            return 0

        remaining_window = self._ends_at - time()
        releasable = max(
            1,
            max_size
            - floor(
                self._hit_count_for_last_window * (1 - self._elapsed_window_ratio())
            ),
        )
        needed = tokens - remaining

        if releasable >= needed:
            return needed * (remaining_window / releasable)

        return remaining_window + (needed - releasable) * (self._interval / max_size)

    def _elapsed_window_ratio(self) -> float:
        window_start = self._ends_at - self._interval

        return min((time() - window_start) / self._interval, 1)

    def add(self, hits: int = 0) -> None:
        self._hit_count += hits

    @classmethod
    def from_previous_window(cls, previous_window: "Window", interval: int) -> Self:
        window = cls(id=previous_window._id, interval=interval)
        ends_at = previous_window._ends_at + interval

        if time() < ends_at:
            window._hit_count_for_last_window = previous_window._hit_count
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
