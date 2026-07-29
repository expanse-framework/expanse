from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from expanse.jobs.core.job import Job
from expanse.types.jobs.job_options import JobOptions


if TYPE_CHECKING:
    from collections.abc import Callable


JobT = TypeVar("JobT", bound=type[Job[Any]])


def _options_of(cls: type[Job[Any]]) -> JobOptions:
    if not hasattr(cls, "options"):
        return JobOptions()

    return JobOptions(**cls.options)


def transport(name: str) -> Callable[[JobT], JobT]:
    """
    Class decorator setting the default transport for a job.

    :param name: The name of the transport to use for dispatching the job.
    """
    if not name:
        raise ValueError("The transport name cannot be empty.")

    def decorator(cls: JobT) -> JobT:
        options = _options_of(cls)
        options["transport"] = name
        cls.options = options

        return cls

    return decorator


def delay(seconds: int) -> Callable[[JobT], JobT]:
    """
    Class decorator setting the default delay for a job.

    :param seconds: The number of seconds to delay the dispatch.
    """
    if seconds < 0:
        raise ValueError("The delay must be a non-negative number of seconds.")

    def decorator(cls: JobT) -> JobT:
        options = _options_of(cls)
        options["delay"] = seconds
        cls.options = options

        return cls

    return decorator


def unique() -> Callable[[JobT], JobT]:
    """
    Class decorator marking a job as unique.
    """

    def decorator(cls: JobT) -> JobT:
        options = _options_of(cls)
        options["unique"] = True
        cls.options = options

        return cls

    return decorator
