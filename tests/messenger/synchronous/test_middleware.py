from dataclasses import dataclass

import pytest

from expanse.cache.synchronous.cache import Cache
from expanse.cache.synchronous.stores.memory import MemoryStore
from expanse.container.container import Container
from expanse.contracts.cache.synchronous.cache import Cache as CacheContract
from expanse.logging.context import Context
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.context import ContextStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.stamps.unique_lock_acquired import UniqueLockAcquiredStamp
from expanse.messenger.synchronous.locks.unique import UniqueLock
from expanse.messenger.synchronous.middleware.ensure_unique import EnsureUnique
from expanse.messenger.synchronous.middleware.propagate_context import PropagateContext


@dataclass
class MyMessage:
    foo: str


@pytest.fixture()
def cache() -> Cache:
    return Cache("test", MemoryStore())


@pytest.fixture()
def ensure_unique(cache: Cache) -> EnsureUnique:
    container = Container()
    container.instance(CacheContract, cache)

    return EnsureUnique(container)


def _passthrough(envelope: Envelope) -> Envelope:
    return envelope


def test_ensure_unique_ignores_messages_without_unique_stamp(
    ensure_unique: EnsureUnique,
) -> None:
    envelope = ensure_unique.handle(Envelope(MyMessage(foo="bar")), _passthrough)

    assert not envelope.has_stamp(UniqueLockAcquiredStamp)


def test_ensure_unique_acquires_the_lock(
    ensure_unique: EnsureUnique, cache: Cache
) -> None:
    envelope = Envelope(MyMessage(foo="bar"), [UniqueStamp()])

    assert ensure_unique.handle(envelope, _passthrough).has_stamp(
        UniqueLockAcquiredStamp
    )
    assert not UniqueLock(cache).acquire(envelope)


def test_ensure_unique_skips_messages_whose_lock_is_held(
    ensure_unique: EnsureUnique, cache: Cache
) -> None:
    envelope = Envelope(MyMessage(foo="bar"), [UniqueStamp()])
    UniqueLock(cache).acquire(envelope)

    def fail(envelope: Envelope) -> Envelope:
        raise AssertionError("The message should not be sent")

    assert not ensure_unique.handle(envelope, fail).has_stamp(UniqueLockAcquiredStamp)


def test_ensure_unique_releases_the_lock_when_sending_fails(
    ensure_unique: EnsureUnique, cache: Cache
) -> None:
    envelope = Envelope(MyMessage(foo="bar"), [UniqueStamp()])

    def fail(envelope: Envelope) -> Envelope:
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        ensure_unique.handle(envelope, fail)

    assert UniqueLock(cache).acquire(envelope)


def test_propagate_context_stamps_the_current_context() -> None:
    context = Context()
    context["request_id"] = "abc"

    envelope = PropagateContext(context).handle(
        Envelope(MyMessage(foo="bar")), _passthrough
    )

    stamp = envelope.stamp(ContextStamp)
    assert stamp is not None
    assert stamp.context == {"request_id": "abc"}
