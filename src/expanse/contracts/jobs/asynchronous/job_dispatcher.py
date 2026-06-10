from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from expanse.contracts.jobs.asynchronous.job import Job


class JobDispatcher(ABC):
    @abstractmethod
    async def dispatch(self, job: "Job[Any]") -> None:
        """
        Dispatch a job for execution.

        :param job: The job to dispatch.
        """
        ...
