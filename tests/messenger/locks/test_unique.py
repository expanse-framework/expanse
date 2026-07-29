from __future__ import annotations

from dataclasses import dataclass

import pytest

from expanse.cache.asynchronous.cache import Cache
from expanse.cache.asynchronous.stores.memory import MemoryStore
from expanse.cache.synchronous.stores.memory import MemoryStore as SyncMemoryStore
from expanse.messenger.envelope import Envelope
from expanse.messenger.locks.exceptions import UniqueLockError
from expanse.messenger.locks.unique import UniqueLock
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.support._utils import class_to_name


@dataclass
class UniqueMessage:
    value: str


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore(SyncMemoryStore()))


@pytest.fixture()
def lock(cache: Cache) -> UniqueLock:
    return UniqueLock(cache)


def _envelope(value: str = "hello", *, with_stamp: bool = True) -> Envelope:
    stamps = [UniqueStamp()] if with_stamp else []
    return Envelope(UniqueMessage(value), stamps=stamps)


async def test_acquire_returns_true_when_lock_is_free(lock: UniqueLock) -> None:
    assert await lock.acquire(_envelope()) is True


async def test_acquire_returns_false_when_lock_is_already_held(
    cache: Cache,
) -> None:
    lock = UniqueLock(cache)
    other = UniqueLock(cache)

    assert await lock.acquire(_envelope()) is True
    assert await other.acquire(_envelope()) is False


async def test_acquire_raises_when_envelope_has_no_unique_stamp(
    lock: UniqueLock,
) -> None:
    with pytest.raises(UniqueLockError, match=r"Envelope must have a UniqueStamp"):
        await lock.acquire(_envelope(with_stamp=False))


async def test_release_frees_the_lock(cache: Cache) -> None:
    lock = UniqueLock(cache)
    other = UniqueLock(cache)

    assert await lock.acquire(_envelope()) is True
    assert await lock.release(_envelope()) is True
    assert await other.acquire(_envelope()) is True


async def test_release_raises_when_envelope_has_no_unique_stamp(
    lock: UniqueLock,
) -> None:
    with pytest.raises(UniqueLockError, match=r"Envelope must have a UniqueStamp"):
        await lock.release(_envelope(with_stamp=False))


def test_get_key_uses_message_class_name(lock: UniqueLock) -> None:
    key = lock.get_key(_envelope())

    assert key == f"expanse:messenger:locks:unique:{class_to_name(UniqueMessage)}"


def test_get_key_raises_when_envelope_has_no_unique_stamp(lock: UniqueLock) -> None:
    with pytest.raises(UniqueLockError, match=r"Envelope must have a UniqueStamp"):
        lock.get_key(_envelope(with_stamp=False))


async def test_lock_key_is_isolated_per_message_class(cache: Cache) -> None:
    @dataclass
    class OtherMessage:
        value: str

    lock = UniqueLock(cache)

    first = Envelope(UniqueMessage("a"), stamps=[UniqueStamp()])
    second = Envelope(OtherMessage("b"), stamps=[UniqueStamp()])

    assert await lock.acquire(first) is True
    assert await lock.acquire(second) is True
