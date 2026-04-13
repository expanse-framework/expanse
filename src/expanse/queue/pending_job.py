from typing import Self

from expanse.contracts.queue.job import Job
from expanse.messenger.envelope import Envelope


class PendingJob:
    def __init__(self, job: Job) -> None:
        from expanse.messenger.stamps.self_handling import SelfHandlingStamp

        self._job: Envelope = Envelope.wrap(job, stamps=[SelfHandlingStamp()])

    def delay(self, seconds: int) -> Self:
        """
        Set a delay for the job.

        :param seconds: The number of seconds to delay the dispatch.

        :return: The PendingJob instance for chaining.
        """
        from expanse.messenger.stamps.delay import DelayStamp

        self._job = self._job.with_stamps(DelayStamp(seconds * 1000))

        return self
