from expanse.contracts.messenger.asynchronous.sender import Sender as SenderContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.transports.memory.queue import MemoryQueue


class MemorySender(SenderContract):
    def __init__(self, queue: MemoryQueue) -> None:
        self._queue: MemoryQueue = queue

    @property
    def queue(self) -> MemoryQueue:
        return self._queue

    @property
    def sent(self) -> list[Envelope]:
        return self._queue.sent

    async def send(self, envelope: Envelope) -> Envelope:
        return self._queue.push(envelope)

    async def close(self) -> None:
        self._queue.clear()
