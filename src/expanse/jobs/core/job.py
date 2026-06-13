from typing import Self

from expanse.contracts.jobs.job import Job as BaseJob
from expanse.types.jobs.job_options import JobOptions


class Job[T](BaseJob[T]):
    def __init__(self, payload: T) -> None:
        super().__init__(payload)

        if not hasattr(self, "options"):
            self.options = JobOptions()
        else:
            self.options = JobOptions(**self.options)

    def via(self, transport: str) -> Self:
        """
        Set the transport for the job.

        :param transport: The name of the transport to use for dispatching the job.
        """
        self.options["transport"] = transport

        return self

    def delay(self, seconds: int) -> Self:
        """
        Set a delay for the job.

        :param seconds: The number of seconds to delay the dispatch.
        """
        self.options["delay"] = seconds

        return self

    async def dispatch(self) -> None:
        """
        Dispatch the job to the configured transport.
        """
        from expanse.core.helpers import _get_container
        from expanse.jobs.asynchronous.job_dispatcher import JobDispatcher

        container = _get_container()

        dispatcher = await container.get(JobDispatcher)

        await dispatcher.dispatch(self)

    def dispatch_sync(self) -> None:
        """
        Dispatch the job to the configured transport synchronously.
        """
        from expanse.core.helpers import _get_container
        from expanse.jobs.synchronous.job_dispatcher import JobDispatcher
        from expanse.support._concurrency import async_to_sync

        container = _get_container()

        dispatcher = async_to_sync(container.get)(JobDispatcher)

        dispatcher.dispatch(self)
