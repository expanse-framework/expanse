from abc import ABC
from abc import abstractmethod
from typing import Self


class WorkerAwareReceiver(ABC):
    """
    Receiver that is aware of the worker running it, especially its ID.

    This is useful for receivers that are not safe to share when a worker
    is running concurrently.
    """

    @abstractmethod
    def clone_for_worker(self, worker_id: str) -> Self: ...
