from abc import ABC
from abc import abstractmethod


class Lock(ABC):
    """
    A lock that can be used to synchronize access to a shared resource across multiple workers or processes.
    """

    @abstractmethod
    def acquire(self, blocking: bool = True, timeout: int | None = None) -> bool:
        """
        Acquire the lock for the given key.

        :param blocking: If True, block until the lock is acquired. If False, return immediately if the lock cannot be acquired.
        :param timeout: The maximum time in seconds to wait for the lock. If None, do not wait.

        :return: True if the lock was acquired successfully, False if the timeout was reached without acquiring the lock.
        """
        ...

    @abstractmethod
    def release(self, force: bool = False) -> bool:
        """
        Release the lock.

        :param force: If True, forcefully release the lock even if it is not held by the current owner.

        :return: True if the lock was released successfully, False otherwise.
        """
        ...

    @abstractmethod
    def refresh(self, ttl: int | None = None) -> bool:
        """
        Refresh the lock's TTL.

        :param ttl: The new time-to-live (TTL) for the lock in seconds. If None, use the original TTL.

        :return: True if the lock was refreshed successfully, False otherwise.
        """
        ...

    def __enter__(self) -> "Lock":
        self.acquire()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
