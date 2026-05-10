from typing import TYPE_CHECKING

from expanse.contracts.jobs.job import Job
from expanse.jobs.pending_job import PendingJob


if TYPE_CHECKING:
    from expanse.jobs.asynchronous.job_dispatcher import AsyncJobDispatcher


class AsyncPendingJob(PendingJob):
    def __init__(self, dispatcher: "AsyncJobDispatcher", job: Job) -> None:
        super().__init__(job)

        self._dispatcher: AsyncJobDispatcher = dispatcher

    async def dispatch(self) -> None:
        """
        Dispatch the job to the appropriate queue for execution.
        """
        self._dispatched = True

        await self._dispatcher._bus.dispatch(self._job)
