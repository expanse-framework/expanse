from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock


class Locker(ABC):
    @abstractmethod
    def lock(self, name: str, ttl: int | None = None) -> "Lock":
        """
        Create a lock with the given name and time-to-live (TTL).

        :param name: The name of the lock.
        :param ttl: The time-to-live (TTL) for the lock in seconds. After this time, the lock will be automatically released.
                    If None, the lock will not expire.

        :return: A Lock instance representing the created lock.
        """
