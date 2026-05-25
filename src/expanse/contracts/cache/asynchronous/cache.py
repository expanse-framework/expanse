from abc import ABC
from abc import abstractmethod
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import overload


if TYPE_CHECKING:
    from expanse.contracts.lock.asynchronous.lock import Lock


_T = TypeVar("_T")


class Cache(ABC):
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store an item in the cache.

        :param key: The key under which the value should be stored.
        :param value: The value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.
        :param until: The datetime until which the cache item should be valid.

        :return: True if the item was successfully stored, False otherwise.
        """

    @abstractmethod
    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store multiple items in the cache.

        :param items: A dictionary of key-value pairs to be stored.
        :param ttl: The time-to-live (TTL) for the cache items in seconds.
        :param until: The datetime until which the cache items should be valid.

        :return: True if the items were successfully stored, False otherwise.
        """

    @overload
    async def get(self, key: str) -> Any | None: ...

    @overload
    async def get(self, key: str, default: Any) -> Any: ...

    @abstractmethod
    async def get(self, key: str, default: Any | None = None) -> Any | None:
        """
        Retrieve an item from the cache.

        :param key: The key of the item to retrieve.
        :param default: The value to return if the key does not exist in the cache.

        :return: The value associated with the key, or the default value if the key does not exist.
        """

    @abstractmethod
    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        """
        Retrieve multiple items from the cache.

        :param keys: A list of keys to retrieve.
        :param default: The value to return for keys that do not exist in the cache.

        :return: A dictionary mapping each key to its associated value, or the default value if the key does not exist.
        """

    @overload
    async def remember(
        self,
        key: str,
        callback: Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T: ...

    @overload
    async def remember(
        self,
        key: str,
        callback: Callable[..., _T],
        ttl: int | None = None,
    ) -> _T: ...

    @abstractmethod
    async def remember(
        self,
        key: str,
        callback: Callable[..., _T] | Callable[..., Awaitable[_T]],
        ttl: int | None = None,
    ) -> _T:
        """
        Store the result of a callback in the cache if the key does not already exist.

        If a locker is configured for the cache, this method will acquire a lock for the key before checking
        if it exists in the cache and executing the callback.
        This ensures that only one process can execute the callback and store
        the result in the cache for a given key at a time, avoiding cache stampedes.

        :param key: The key under which the value should be stored.
        :param callback: The callback to generate the value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.

        :return: The value returned by the callback, either from the cache or freshly generated.
        """

    @abstractmethod
    async def has(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        :param key: The key to check for existence.

        :return: True if the key exists in the cache, False otherwise.
        """

    @abstractmethod
    async def pop(self, key: str) -> Any | None:
        """
        Remove an item from the cache and return its value.

        :param key: The key of the item to remove.

        :return: The value associated with the key, or None if the key does not exist.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        :param key: The key to delete.

        :return: True if the key was successfully deleted, False otherwise.
        """

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> bool:
        """
        Delete multiple keys from the cache.

        :param keys: The keys to delete.

        :return: True if all keys were successfully deleted, False otherwise.
        """

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all items from the cache.
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
        :param ttl: The time-to-live (TTL) for the lock in seconds.
        :param owner: The owner of the lock. If None, the lock will be owned by the current process.
        :param refresh: Whether to automatically refresh the lock's TTL while it is held.

        :return: A Lock instance that can be used to synchronize access to the resource associated with the name.
        """
