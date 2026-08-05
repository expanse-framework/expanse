from abc import ABC
from abc import abstractmethod
from typing import Self


class WorkerAwareTransport(ABC):
    """
    Transport that is aware of the worker's running it, especially its ID.

    This is useful for transports that are not safe to share when a worker
    is running concurrently.
    """

    @abstractmethod
    def clone_for_worker(self, worker_id: str) -> Self: ...
