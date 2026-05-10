from typing import Any
from typing import Protocol


class SyncJob(Protocol):
    def handle(self, *args: Any, **kwargs: Any) -> None:
        """
        Handle the job. This method will be called by the worker when the job is executed.
        """
        ...


class AsyncJob(Protocol):
    async def handle(self, *args: Any, **kwargs: Any) -> None:
        """
        Handle the job. This method will be called by the worker when the job is executed.
        """
        ...


type Job = SyncJob | AsyncJob
