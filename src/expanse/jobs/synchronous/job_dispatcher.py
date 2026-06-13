from typing import Any

from expanse.contracts.messenger.synchronous.message_bus import MessageBus
from expanse.jobs.core.job import Job
from expanse.jobs.core.job_dispatcher import JobDispatcher as BaseJobDispatcher


class JobDispatcher(BaseJobDispatcher):
    def __init__(self, bus: MessageBus) -> None:
        self._bus: MessageBus = bus

    def dispatch(self, job: Job[Any]) -> None:
        """
        Dispatch a job through the bus immediately.

        :param job: The job to dispatch.
        """
        envelope = self.prepare(job)

        self._bus.dispatch(envelope)


__all__ = ["JobDispatcher"]
