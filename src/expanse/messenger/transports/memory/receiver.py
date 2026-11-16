from collections.abc import AsyncIterator

from expanse.contracts.messenger.asynchronous.receiver import (
    Receiver as ReceiverContract,
)
from expanse.messenger.envelope import Envelope
from expanse.messenger.transports.memory.queue import MemoryQueue


class MemoryReceiver(ReceiverContract):
    def __init__(self, queue: MemoryQueue) -> None:
        self._queue: MemoryQueue = queue

    @property
    def queue(self) -> MemoryQueue:
        return self._queue

    async def receive(self) -> AsyncIterator[Envelope]:
        for envelope in self._queue.pull():
            yield envelope

    async def acknowledge(self, envelope: Envelope) -> None:
        self._queue.acknowledge(envelope)

    async def reject(self, envelope: Envelope) -> None:
        self._queue.reject(envelope)

    async def close(self) -> None:
        self._queue.clear()
