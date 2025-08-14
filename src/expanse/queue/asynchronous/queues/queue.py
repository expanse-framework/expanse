import inspect
import uuid

from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable

from expanse.types.queue.job import JobType


class AsyncQueue(ABC):
    @abstractmethod
    async def put(self, job: JobType, data: str = "", queue: str | None = None) -> None:
        """
        Put a job into the queue.
        """
        ...

    async def _put_using(
        self,
        job: JobType,
        payload: dict[str, str | tuple[str, str]],
        queue: str | None,
        func: Callable[[dict[str, str | tuple[str, str]], str | None], Awaitable[None]],
    ) -> None:
        await func(payload, queue)

    async def _create_payload(
        self, job: JobType, queue: str, data: str = ""
    ) -> dict[str, str | tuple[str, str]]:
        """
        Create a payload for the job.
        """
        payload = {
            "id": str(uuid.uuid4()),
            "display_name": self._get_display_name(job),
            "job": self._get_callable(job),
            "data": data,
        }

        return payload

    def _get_callable(self, job: JobType) -> tuple[str, str]:
        """
        Get the callable for the job.
        """
        if inspect.isfunction(job):
            return job.__module__, job.__name__

        return job.__class__.__module__, job.__class__.__name__

    def _get_display_name(self, job: JobType) -> str:
        """
        Get the display name for the job.
        """
        if hasattr(job, "display_name") and job.display_name:
            return job.display_name

        return f"{job.__class__.__name__}"
