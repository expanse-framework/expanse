from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobStamp:
    """
    A stamp used to mark messages with a job, i.e. to be processed as a job.
    """

    # The fully qualified name of the job class to be processed.
    job: str
