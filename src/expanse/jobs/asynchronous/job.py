from abc import ABC
from abc import abstractmethod
from typing import Any

from expanse.jobs.core.job import Job as BaseJob


class Job[T](BaseJob[T], ABC):
    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> None:
        """
        Execute the job.

        This method will be called by the worker when the job is executed.
        """
