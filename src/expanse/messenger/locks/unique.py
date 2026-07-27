from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.messenger.envelope import Envelope
from expanse.messenger.locks.exceptions import UniqueLockError
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.support._utils import class_to_name


class UniqueLock:
    def __init__(self, cache: Cache) -> None:
        self._cache: Cache = cache

    async def acquire(self, envelope: Envelope) -> bool:
        """
        Attempt to acquire the lock for the given envelope.

        :param envelope: the Envelope instance containing the UniqueStamp.

        :return: Whether the lock was acquired or not
        """
        stamp = envelope.stamp(UniqueStamp)

        if stamp is None:
            raise UniqueLockError("Envelope must have a UniqueStamp.")

        return await self._cache.lock(self.get_key(envelope)).acquire(False)

    async def release(self, envelope: Envelope) -> bool:
        """
        Release the lock for the given envelope.

        :param envelope: the Envelope instance containing the UniqueStamp.
        """
        stamp = envelope.stamp(UniqueStamp)

        if stamp is None:
            raise UniqueLockError("Envelope must have a UniqueStamp.")

        return await self._cache.lock(self.get_key(envelope)).release(force=True)

    def get_key(self, envelope: Envelope) -> str:
        stamp = envelope.stamp(UniqueStamp)
        key = class_to_name(envelope.open().__class__)

        if stamp is None:
            raise UniqueLockError("Envelope must have a UniqueStamp.")

        return f"expanse:messenger:locks:unique:{key}"
