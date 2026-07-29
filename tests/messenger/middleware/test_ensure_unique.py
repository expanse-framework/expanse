from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache as CacheContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.middleware.ensure_unique import EnsureUnique
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.unique import UniqueStamp


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


@dataclass
class UniqueMessage:
    value: str


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore(SyncMemoryStore()))


@pytest.fixture()
def container(cache: Cache) -> Container:
    container = Container()
    container.instance(CacheContract, cache)
    return container


@pytest.fixture()
def middleware(container: Container) -> EnsureUnique:
    return EnsureUnique(container)


def _pass_through() -> Callable[[Envelope], Awaitable[Envelope]]:
    async def next_call(envelope: Envelope) -> Envelope:
        next_call.calls.append(envelope)  # type: ignore[attr-defined]
        return envelope

    next_call.calls = []  # type: ignore[attr-defined]
    return next_call


async def test_calls_next_when_envelope_has_no_unique_stamp(
    middleware: EnsureUnique,
) -> None:
    envelope = Envelope(UniqueMessage("hello"))
    next_call = _pass_through()

    result = await middleware.handle(envelope, next_call)

    assert result is envelope
    assert next_call.calls == [envelope]  # type: ignore[attr-defined]


async def test_calls_next_when_envelope_has_received_stamp(
    middleware: EnsureUnique,
) -> None:
    envelope = Envelope(UniqueMessage("hello"), stamps=[UniqueStamp(), ReceivedStamp()])
    next_call = _pass_through()

    result = await middleware.handle(envelope, next_call)

    assert result is envelope
    assert next_call.calls == [envelope]  # type: ignore[attr-defined]


async def test_calls_next_after_acquiring_the_lock(
    middleware: EnsureUnique,
) -> None:
    envelope = Envelope(UniqueMessage("hello"), stamps=[UniqueStamp()])
    next_call = _pass_through()

    result = await middleware.handle(envelope, next_call)

    assert result is envelope
    assert next_call.calls == [envelope]  # type: ignore[attr-defined]


async def test_skips_next_when_lock_cannot_be_acquired(
    middleware: EnsureUnique, container: Container
) -> None:
    envelope = Envelope(UniqueMessage("hello"), stamps=[UniqueStamp()])
    first_next = _pass_through()
    second_next = _pass_through()

    # First call acquires the lock and processes the envelope.
    await middleware.handle(envelope, first_next)

    # A second call for the same message class cannot acquire the lock,
    # so the middleware short-circuits and returns the envelope untouched.
    other = Envelope(UniqueMessage("hello"), stamps=[UniqueStamp()])
    result = await middleware.handle(other, second_next)

    assert result is other
    assert second_next.calls == []  # type: ignore[attr-defined]
