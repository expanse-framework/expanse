from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from expanse.contracts.cache.cache_item import CacheItem


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock


class Store(ABC):
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a value in the store.

        :param key: The key to set.
        :param value: The value to set.
        :param ttl: The time-to-live (TTL) for the cache item in seconds. If None, the item will not expire.

        :return: True if the item was successfully stored, False otherwise.
        """

    @abstractmethod
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        """
        Set multiple values in the store.

        :param items: A dictionary of key-value pairs to set.
        :param ttl: The time-to-live (TTL) for the cache items in seconds. If None, the items will not expire.

        :return: True if the items were successfully stored, False otherwise.
        """

    @abstractmethod
    async def get(self, key: str) -> CacheItem:
        """
        Get a value from the store.

        :param key: The key to get.

        :return: A CacheItem instance representing the value associated with the key.
        """

    @abstractmethod
    async def get_many(self, keys: list[str]) -> dict[str, CacheItem]:
        """
        Get multiple values from the store.

        :param keys: The keys to get.
        :return: A dictionary mapping each key to its associated cache item.
        """

    @abstractmethod
    async def has(self, key: str) -> bool:
        """
        Check if a key exists in the store.

        :param key: The key to check.

        :return: True if the key exists, False otherwise.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the store.

        :param key: The key to delete.

        :return: True if the key was successfully deleted, False otherwise.
        """

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all values from the store.

        :return: True if the store was successfully cleared, False otherwise.
        """

    @abstractmethod
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> "Lock":
        """
        Get a lock for the given name.

        :param name: The name of the lock.
        :param ttl: The time-to-live (TTL) for the lock in seconds. If None, the lock will not expire.
        :param owner: The owner of the lock. If None, the lock will be owned by the current process.
        :param refresh: Whether to automatically refresh the lock's TTL while it is held.

        :return: A Lock instance for the given name.
        """
