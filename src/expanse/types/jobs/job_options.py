from typing import NotRequired
from typing import TypedDict


class JobOptions(TypedDict):
    """
    Options for configuring a job.

    :param transport: The name of the transport to use for dispatching the job. If not specified, the default transport will be used.
    :param delay: The delay in seconds before the job is dispatched. This can be used to schedule jobs to run at a later time.
    """

    transport: NotRequired[str]
    delay: NotRequired[int]
