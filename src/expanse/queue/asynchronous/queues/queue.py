import inspect
import uuid

from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Self

from expanse.container.container import Container
from expanse.types.queue.job import JobType


class AsyncQueue(ABC):
    _container: Container | None = None

    def __init__(self, dispatch_after_commit: bool = False) -> None:
        self._dispatch_after_commit: bool = False

    @abstractmethod
    async def size(self, queue: str | None = None) -> int:
        """
        Get the size of the queue.
        """
        ...

    @abstractmethod
    async def put(self, job: JobType, data: str = "", queue: str | None = None) -> None:
        """
        Put a job into the queue.
        """
        ...

    def set_container(self, container: Container) -> Self:
        """
        Set the container for the queue.
        """
        self._container = container

        return self

    async def _put_using(
        self,
        job: JobType,
        payload: dict[str, str | tuple[str, str]],
        queue: str | None,
        func: Callable[[dict[str, str | tuple[str, str]], str | None], Awaitable[None]],
    ) -> None:
        from expanse.database.session import Session

        assert (
            self._container is not None
        ), "Container must be set before using the queue."

        if not self._dispatch_after_commit or not self._container.has(Session):
            await func(payload, queue)
            return

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

        if inspect.isfunction(job):
            return job.__name__

        return f"{job.__class__.__name__}"

    def _should_dispatch_after_commit(self, job: JobType) -> bool:
        """
        Check if the job should be dispatched after commit.
        """
        if inspect.isfunction(job):
            return self._dispatch_after_commit

        return getattr(job, "dispatch_after_commit", self._dispatch_after_commit)
