from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.rate_limiting.exceptions import TokenConsumptionOverLimitError
from expanse.rate_limiting.rate_limiters.sliding_window import rate_limiter as module
from expanse.rate_limiting.rate_limiters.sliding_window.rate_limiter import (
    SlidingWindowRateLimiter,
)
from expanse.support.duration import SingleUnitDuration


if TYPE_CHECKING:
    from collections.abc import Iterator


class Clock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now: float = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[Clock]:
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)

    yield clock


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore(SyncMemoryStore()))


@pytest.fixture()
def limiter(cache: Cache) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(10, SingleUnitDuration(60, "seconds"), cache)


async def test_consume_accepts_requests_under_the_limit(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    for i in range(10):
        rate_limit = await limiter.consume("id")

        assert rate_limit.accepted is True
        assert rate_limit.limit == 10
        assert rate_limit.available_tokens == 9 - i


async def test_consume_rejects_requests_over_the_limit(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    rate_limit = await limiter.consume("id")

    assert rate_limit.accepted is False
    assert rate_limit.available_tokens == 0


async def test_retry_after_is_now_while_tokens_are_available(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    rate_limit = await limiter.consume("id", 9)

    assert rate_limit.retry_after.timestamp() == pytest.approx(clock.now, abs=1)


async def test_retry_after_is_the_time_for_the_next_token(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    # The window is exhausted: a single token is released every 60 / 10 seconds,
    # not after the whole window has been drained.
    accepted = await limiter.consume("id", 10)
    rejected = await limiter.consume("id")

    assert accepted.retry_after.timestamp() == pytest.approx(clock.now + 6, abs=1)
    assert rejected.retry_after.timestamp() == pytest.approx(clock.now + 6, abs=1)


async def test_retry_after_accounts_for_the_number_of_requested_tokens(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    rate_limit = await limiter.consume("id", 3)

    assert rate_limit.accepted is False
    assert rate_limit.retry_after.timestamp() == pytest.approx(clock.now + 18, abs=1)


async def test_previous_window_hits_are_carried_over(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    # A fixed window limiter would allow 10 more tokens right after the window
    # ended, while only the fraction of the previous window that has slid out
    # should be available.
    clock.advance(61)

    rate_limit = await limiter.consume("id")

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 0

    rate_limit = await limiter.consume("id")

    assert rate_limit.accepted is False


async def test_previous_window_hits_decay_over_the_new_window(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    # Half of the previous window has slid out, freeing half of its hits.
    clock.advance(90)

    rate_limit = await limiter.consume("id", 5)

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 0


async def test_tokens_are_fully_released_after_two_windows(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    clock.advance(121)

    rate_limit = await limiter.consume("id", 10)

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 0


async def test_consume_without_token_does_not_consume_anything(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 4)

    rate_limit = await limiter.consume("id", 0)

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 6
    assert rate_limit.retry_after.timestamp() == pytest.approx(clock.now, abs=1)

    rate_limit = await limiter.consume("id", 6)

    assert rate_limit.accepted is True


async def test_consume_without_token_reports_the_next_available_token(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    rate_limit = await limiter.consume("id", 0)

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 0
    assert rate_limit.retry_after.timestamp() == pytest.approx(clock.now + 6, abs=1)


async def test_limits_are_scoped_to_the_given_id(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)

    rate_limit = await limiter.consume("other-id")

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 9


async def test_reset_clears_the_window(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    await limiter.consume("id", 10)
    await limiter.reset("id")

    rate_limit = await limiter.consume("id")

    assert rate_limit.accepted is True
    assert rate_limit.available_tokens == 9


async def test_consume_more_tokens_than_the_limit_raises_an_error(
    limiter: SlidingWindowRateLimiter, clock: Clock
) -> None:
    with pytest.raises(TokenConsumptionOverLimitError):
        await limiter.consume("id", 11)
