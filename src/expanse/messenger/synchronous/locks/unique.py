from expanse.contracts.cache.synchronous.cache import Cache
from expanse.messenger.envelope import Envelope
from expanse.messenger.locks.unique import get_unique_lock_key


class UniqueLock:
    def __init__(self, cache: Cache) -> None:
        self._cache: Cache = cache

    def acquire(self, envelope: Envelope) -> bool:
        """
        Attempt to acquire the lock for the given envelope.

        :param envelope: the Envelope instance containing the UniqueStamp.

        :return: Whether the lock was acquired or not
        """
        return self._cache.lock(self.get_key(envelope)).acquire(False)

    def release(self, envelope: Envelope) -> bool:
        """
        Release the lock for the given envelope.

        :param envelope: the Envelope instance containing the UniqueStamp.
        """
        return self._cache.lock(self.get_key(envelope)).release(force=True)

    def get_key(self, envelope: Envelope) -> str:
        return get_unique_lock_key(envelope)
