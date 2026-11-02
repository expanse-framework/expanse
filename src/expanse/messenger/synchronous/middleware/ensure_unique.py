from collections.abc import Callable

from expanse.container.container import Container
from expanse.contracts.cache.synchronous.cache import Cache
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.stamps.unique_lock_acquired import UniqueLockAcquiredStamp
from expanse.messenger.synchronous.locks.unique import UniqueLock
from expanse.support._concurrency import async_to_sync


class EnsureUnique:
    """
    Middleware to ensure that only one message of a particular type is processed at the same time.
    """

    def __init__(self, container: Container) -> None:
        self._container: Container = container

    def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Envelope]
    ) -> Envelope:
        if not envelope.has_stamp(UniqueStamp):
            return next_call(envelope)

        lock = UniqueLock(async_to_sync(self._container.get)(Cache))

        if not lock.acquire(envelope):
            return envelope

        try:
            sent_envelope = next_call(envelope)
        except BaseException:
            # The message was not sent, so nothing will ever release the lock.
            lock.release(envelope)

            raise

        return sent_envelope.with_stamps(UniqueLockAcquiredStamp())
