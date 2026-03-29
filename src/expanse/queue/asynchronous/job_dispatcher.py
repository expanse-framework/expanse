from expanse.contracts.queue.job import Job
from expanse.messenger.asynchronous.message_bus import MessageBus
from expanse.queue.asynchronous.pending_job import AsyncPendingJob


class AsyncJobDispatcher:
    """
    The AsyncJobDispatcher is responsible for dispatching jobs to the appropriate queue.

    This a small wrapper around the MessageBus to provide a simpler interface for job dispatching.
    """

    def __init__(self, bus: MessageBus) -> None:
        self._bus: MessageBus = bus

    async def dispatch(self, job: Job) -> None:
        """
        Dispatch a job through the bus immediately.

        :param job: The job to dispatch.
        """
        await self.prepare(job).dispatch()

    def prepare(self, job: Job) -> AsyncPendingJob:
        """
        Prepare a job for dispatching.

        :param job: The job to prepare for later dispatching.

        :return: A PendingDispatch instance used to configure the job before dispatching.
        """
        return AsyncPendingJob(self, job)


__all__ = ["AsyncJobDispatcher"]
