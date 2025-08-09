from expanse.container.container import Container
from expanse.types.queue.job import JobType


class Dispatcher:
    def __init__(self, container: Container) -> None:
        self._container: Container = container

    async def dispatch(self, job: JobType) -> Any:
        """
        Dispatch a job.

        If the job should be queued, it will be added to the proper queue,
        otherwise it will be executed immediately.
        """
        return self._container.dispatch(job, *args, **kwargs)
