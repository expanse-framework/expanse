from collections.abc import Awaitable
from collections.abc import Callable

from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.messenger.envelope import Envelope
from expanse.messenger.locks.unique import UniqueLock
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.unique import UniqueStamp


class EnsureUnique:
    """
    Middleware to ensure that only one message of a particular type is processed at the same time.
    """

    def __init__(self, container: Container) -> None:
        self._container: Container = container

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        if not envelope.has_stamp(UniqueStamp):
            return await next_call(envelope)

        if envelope.has_stamp(ReceivedStamp):
            return await next_call(envelope)

        lock = UniqueLock(await self._container.get(Cache))

        if not await lock.acquire(envelope):
            return envelope

        return await next_call(envelope)
