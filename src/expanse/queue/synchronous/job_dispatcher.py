from expanse.contracts.messenger.synchronous.message_bus import MessageBus
from expanse.contracts.queue.job import Job
from expanse.queue.synchronous.pending_job import PendingJob


class JobDispatcher:
    """
    The JobDispatcher is responsible for dispatching jobs to the appropriate queue.

    This a small wrapper around the MessageBus to provide a simpler interface for job dispatching.
    """

    def __init__(self, bus: MessageBus) -> None:
        self._bus: MessageBus = bus

    def dispatch(self, job: Job) -> None:
        """
        Dispatch a job through the bus immediately.

        :param job: The job to dispatch.
        """
        self.prepare(job).dispatch()

    def prepare(self, job: Job) -> "PendingJob":
        """
        Prepare a job for dispatching.

        :param job: The job to prepare for later dispatching.

        :return: A PendingDispatch instance used to configure the job before dispatching.
        """
        return PendingJob(self, job)


__all__ = ["JobDispatcher"]
