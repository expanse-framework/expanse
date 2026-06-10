from abc import ABC
from abc import abstractmethod

from expanse.jobs.core.job import Job as BaseJob


class Job[T](BaseJob[T], ABC):
    @abstractmethod
    async def execute(self) -> None:
        """
        Execute the job.

        This method will be called by the worker when the job is executed.
        """
        ...
