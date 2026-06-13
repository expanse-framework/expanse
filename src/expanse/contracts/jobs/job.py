from abc import ABC

from expanse.types.jobs.job_options import JobOptions


class Job[T](ABC):
    options: JobOptions

    def __init__(self, payload: T) -> None:
        self.payload: T = payload
