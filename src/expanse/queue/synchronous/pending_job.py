from typing import TYPE_CHECKING

from expanse.contracts.queue.job import Job
from expanse.queue.pending_job import PendingJob as BasePendingJob


if TYPE_CHECKING:
    from expanse.queue.synchronous.job_dispatcher import JobDispatcher


class PendingJob(BasePendingJob):
    def __init__(self, dispatcher: "JobDispatcher", job: Job) -> None:
        super().__init__(job)

        self._dispatcher: JobDispatcher = dispatcher

    def dispatch(self) -> None:
        """
        Dispatch the job to the appropriate queue for execution.
        """
        self._dispatcher._bus.dispatch(self._job)
